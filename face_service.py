import os
import time
import cv2
import numpy as np
import face_recognition
from db_manager import DatabaseManager

class FaceService:
    def __init__(self, tolerance=0.52, greeting_cooldown=60, min_confirm_frames=5):
        self.tolerance = tolerance
        self.greeting_cooldown = greeting_cooldown  # Segundos antes de mostrar bienvenida de nuevo al mismo cliente
        self.min_confirm_frames = min_confirm_frames
        
        self.db = DatabaseManager()
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.faces_dir = os.path.join(base_dir, "data", "clientes")
        os.makedirs(self.faces_dir, exist_ok=True)
        
        # Encodings y metadatos en memoria
        self.known_face_encodings = []
        self.known_face_metadata = []
        
        # Registro de tiempos del último saludo {cliente_id: timestamp_float}
        self.last_greeting_time = {}
        
        # Buffer para auto-registro de desconocidos
        self.unknown_candidates = []
        
        # Banners visuales
        self.active_banner = None
        self.recent_events = []
        
        self.recargar_clientes()

    def recargar_clientes(self):
        """Carga o refresca todos los clientes de la base de datos en memoria."""
        clientes = self.db.cargar_clientes()
        self.known_face_encodings = [c["encoding"] for c in clientes]
        self.known_face_metadata = clientes
        print(f"[FaceService] {len(clientes)} clientes cargados en memoria.")

    def set_banner(self, text, duration=4.0, banner_type="success"):
        self.active_banner = {
            "text": text,
            "expires": time.time() + duration,
            "type": banner_type
        }
        self.recent_events.append({
            "text": text,
            "time": time.strftime("%H:%M:%S")
        })
        if len(self.recent_events) > 5:
            self.recent_events.pop(0)

    def procesar_frame(self, frame, process_detection=True):
        """
        Procesa el frame de video.
        Retorna la lista de rostros detectados con sus datos y estado.
        """
        now = time.time()
        
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = []
        face_encodings = []
        
        if process_detection:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        results = []
        current_frame_matched_unknowns = []

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            orig_top = top * 4
            orig_right = right * 4
            orig_bottom = bottom * 4
            orig_left = left * 4
            box = (orig_top, orig_right, orig_bottom, orig_left)
            
            matched_client = None
            min_dist = 1.0

            if len(self.known_face_encodings) > 0:
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = int(np.argmin(face_distances))
                min_dist = float(face_distances[best_match_index])
                
                if min_dist <= self.tolerance:
                    matched_client = self.known_face_metadata[best_match_index]

            if matched_client:
                c_id = matched_client["id"]
                last_time = self.last_greeting_time.get(c_id, 0)
                if now - last_time > self.greeting_cooldown:
                    resumen = self.db.obtener_resumen_cliente(c_id)
                    matched_client["total_compras"] = resumen["total_compras"]
                    matched_client["total_gastado"] = resumen["total_gastado"]
                    self.last_greeting_time[c_id] = now
                    
                    compras_txt = f" - Compras: {resumen['total_compras']}" if resumen['total_compras'] > 0 else " - ¡Bienvenido!"
                    self.set_banner(f"Cliente: {matched_client['nombre']} ({matched_client['codigo']}){compras_txt}", 
                                    duration=3.5, banner_type="info")
                
                results.append({
                    "status": "known",
                    "box": box,
                    "client": matched_client,
                    "distance": min_dist,
                    "progress": 1.0
                })
            else:
                cand_idx = self._asociar_candidato_desconocido(face_encoding)
                if cand_idx is not None:
                    cand = self.unknown_candidates[cand_idx]
                    cand["frames"] += 1
                    cand["last_seen"] = now
                    cand["encoding"] = face_encoding
                    cand["box"] = box
                    current_frame_matched_unknowns.append(cand_idx)
                    
                    progress = min(1.0, cand["frames"] / self.min_confirm_frames)
                    
                    if cand["frames"] >= self.min_confirm_frames:
                        nuevo_cliente = self._auto_registrar_cliente(frame, box, face_encoding)
                        self.unknown_candidates.pop(cand_idx)
                        results.append({
                            "status": "registered_now",
                            "box": box,
                            "client": nuevo_cliente,
                            "distance": 0.0,
                            "progress": 1.0
                        })
                    else:
                        results.append({
                            "status": "registering",
                            "box": box,
                            "client": None,
                            "distance": min_dist,
                            "progress": progress
                        })
                else:
                    nuevo_cand = {
                        "frames": 1,
                        "encoding": face_encoding,
                        "box": box,
                        "last_seen": now
                    }
                    self.unknown_candidates.append(nuevo_cand)
                    cand_idx = len(self.unknown_candidates) - 1
                    current_frame_matched_unknowns.append(cand_idx)
                    
                    results.append({
                        "status": "registering",
                        "box": box,
                        "client": None,
                        "distance": min_dist,
                        "progress": 1.0 / self.min_confirm_frames
                    })

        self.unknown_candidates = [
            c for idx, c in enumerate(self.unknown_candidates)
            if (now - c["last_seen"] < 1.5) or (idx in current_frame_matched_unknowns)
        ]

        return results

    def _asociar_candidato_desconocido(self, face_encoding):
        for idx, cand in enumerate(self.unknown_candidates):
            dist = float(face_recognition.face_distance([cand["encoding"]], face_encoding)[0])
            if dist < 0.45:
                return idx
        return None

    def _auto_registrar_cliente(self, frame, box, encoding):
        top, right, bottom, left = box
        h, w = frame.shape[:2]
        
        pad_y = int((bottom - top) * 0.25)
        pad_x = int((right - left) * 0.25)
        
        crop_top = max(0, top - pad_y)
        crop_bottom = min(h, bottom + pad_y)
        crop_left = max(0, left - pad_x)
        crop_right = min(w, right + pad_x)
        
        face_img = frame[crop_top:crop_bottom, crop_left:crop_right]
        
        codigo = self.db.generar_siguiente_codigo()
        nombre = f"Cliente {codigo}"
        foto_filename = f"{codigo}.jpg"
        foto_path = os.path.join(self.faces_dir, foto_filename)
        
        cv2.imwrite(foto_path, face_img)
        
        # Codificar en memoria para guardar el binario directo en SQLite Cloud
        success, buffer = cv2.imencode(".jpg", face_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        foto_blob = buffer.tobytes() if success else None

        c_id = self.db.registrar_cliente(codigo, nombre, encoding, foto_path, foto_blob=foto_blob)
        
        nuevo_cliente = {
            "id": c_id,
            "codigo": codigo,
            "nombre": nombre,
            "encoding": encoding,
            "foto_path": foto_path,
            "total_compras": 0,
            "total_gastado": 0.0,
            "fecha_registro": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.known_face_encodings.append(encoding)
        self.known_face_metadata.append(nuevo_cliente)
        self.last_greeting_time[c_id] = time.time()
        
        self.set_banner(f"NUEVO CLIENTE REGISTRADO: {nombre} ({codigo})", duration=4.0, banner_type="success")
        print(f"[FaceService] Auto-registrado exitosamente: {codigo} (ID: {c_id})")
        return nuevo_cliente
