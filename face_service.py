import os
import time
import json
import urllib.request
import threading
import cv2
import numpy as np
import face_recognition
from db_manager import DatabaseManager

ULTIMO_EVENTO_ENVIADO = {"estado": None, "cliente_id": None, "time": 0}

def notificar_evento_web(estado, cliente_id=None, codigo=None, mensaje=None, api_url="http://127.0.0.1:8000/api/camara/evento"):
    """Envía una notificación asíncrona con control de tasa a la API Web."""
    now = time.time()
    # Evitar ráfagas duplicadas si el estado no ha cambiado y han pasado menos de 0.8s
    if (ULTIMO_EVENTO_ENVIADO["estado"] == estado and 
        ULTIMO_EVENTO_ENVIADO["cliente_id"] == cliente_id and 
        now - ULTIMO_EVENTO_ENVIADO["time"] < 0.8):
        return

    ULTIMO_EVENTO_ENVIADO["estado"] = estado
    ULTIMO_EVENTO_ENVIADO["cliente_id"] = cliente_id
    ULTIMO_EVENTO_ENVIADO["time"] = now

    def _envio():
        try:
            payload = json.dumps({
                "estado": estado,
                "cliente_id": cliente_id,
                "codigo": codigo,
                "mensaje": mensaje or "¡Hola de nuevo! 👋"
            }).encode('utf-8')
            req = urllib.request.Request(api_url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                resp.read()
        except Exception:
            pass

    threading.Thread(target=_envio, daemon=True).start()


class FaceService:
    def __init__(self, tolerance=0.52, greeting_cooldown=60, min_confirm_frames=5):
        self.tolerance = tolerance
        self.greeting_cooldown = greeting_cooldown
        self.min_confirm_frames = min_confirm_frames
        
        self.db = DatabaseManager()
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.faces_dir = os.path.join(base_dir, "data", "clientes")
        os.makedirs(self.faces_dir, exist_ok=True)
        
        self.known_face_encodings = []
        self.known_face_metadata = []
        
        self.last_greeting_time = {}
        self.unknown_candidates = []
        
        self.active_banner = None
        self.recent_events = []

        self.last_face_seen_time = 0
        
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

        if face_locations:
            self.last_face_seen_time = now

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
                    
                    self.set_banner(f"¡Hola de nuevo! Cliente {matched_client['codigo']}", duration=3.5, banner_type="info")

                # Notificar a la web que el cliente está activo frente a la pantalla
                notificar_evento_web("activo", cliente_id=c_id, codigo=matched_client["codigo"], mensaje="¡Hola de nuevo! 👋")
                
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
                        notificar_evento_web("activo", cliente_id=nuevo_cliente["id"], codigo=nuevo_cliente["codigo"], mensaje="¡Bienvenido! 👋")
                        results.append({
                            "status": "registered_now",
                            "box": box,
                            "client": nuevo_cliente,
                            "distance": 0.0,
                            "progress": 1.0
                        })
                    else:
                        notificar_evento_web("registrando", mensaje="¡Bienvenido! Identificando cliente...")
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
                    
                    notificar_evento_web("registrando", mensaje="¡Bienvenido! Identificando cliente...")
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

        # Si no hay rostros detectados por más de 3 segundos, notificar estado idle a la web
        if not face_locations and (now - self.last_face_seen_time > 3.0):
            notificar_evento_web("idle", mensaje="Esperando cliente...")

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
        
        self.set_banner(f"¡Bienvenido! Cliente {codigo}", duration=4.0, banner_type="success")
        print(f"[FaceService] Auto-registrado exitosamente: {codigo} (ID: {c_id})")
        return nuevo_cliente
