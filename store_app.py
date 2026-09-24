import time
import cv2
import numpy as np
from face_service import FaceService

def draw_corner_rect(img, pt1, pt2, color, thickness=2, line_length=20):
    """Dibuja un recuadro moderno con esquinas reforzadas."""
    x1, y1 = pt1
    x2, y2 = pt2
    
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 1)
    cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
    
    # Esquinas
    cv2.line(img, (x1, y1), (x1 + line_length, y1), color, thickness)
    cv2.line(img, (x1, y1), (x1, y1 + line_length), color, thickness)
    cv2.line(img, (x2, y1), (x2 - line_length, y1), color, thickness)
    cv2.line(img, (x2, y1), (x2, y1 + line_length), color, thickness)
    cv2.line(img, (x1, y2), (x1 + line_length, y2), color, thickness)
    cv2.line(img, (x1, y2), (x1, y2 - line_length), color, thickness)
    cv2.line(img, (x2, y2), (x2 - line_length, y2), color, thickness)
    cv2.line(img, (x2, y2), (x2, y2 - line_length), color, thickness)

def draw_hud(frame, service, results):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    
    # Barra superior oscura
    cv2.rectangle(overlay, (0, 0), (w, 55), (15, 18, 24), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    
    total_cli = len(service.known_face_metadata)
    stats_text = f"SISTEMA DE TIENDA AUTONOMO   |   Clientes: {total_cli}   |   Presiona [Q] Salir  [R] Recargar"
    cv2.putText(frame, stats_text, (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.58, (240, 240, 240), 1, cv2.LINE_AA)
    
    for item in results:
        top, right, bottom, left = item["box"]
        status = item["status"]
        progress = item["progress"]
        
        if status in ("known", "registered_now"):
            client = item["client"]
            color = (0, 225, 120)  # Verde brillante
            draw_corner_rect(frame, (left, top), (right, bottom), color, thickness=3, line_length=25)
            
            nombre = client["nombre"]
            codigo = client["codigo"]
            compras = client.get("total_compras", 0)
            
            title = f"{nombre} ({codigo})"
            subtitle = f"Compras: {compras} tickets"
            
            cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 45), (20, 25, 20), -1)
            cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 45), color, 1)
            
            cv2.putText(frame, title, (left + 6, bottom + 23), cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, subtitle, (left + 6, bottom + 40), cv2.FONT_HERSHEY_DUPLEX, 0.44, (140, 255, 180), 1, cv2.LINE_AA)

        elif status == "empleado":
            empleado = item["client"]
            color = (237, 58, 124)  # Morado: trabajador (es_trabajador = 1)
            draw_corner_rect(frame, (left, top), (right, bottom), color, thickness=3, line_length=25)

            cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 45), (30, 20, 30), -1)
            cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 45), color, 1)

            cv2.putText(frame, f"{empleado['nombre']} ({empleado['codigo']})", (left + 6, bottom + 23),
                        cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, "Trabajador - registra tu huella", (left + 6, bottom + 40),
                        cv2.FONT_HERSHEY_DUPLEX, 0.44, (230, 180, 255), 1, cv2.LINE_AA)

        elif status == "registering":
            color = (0, 190, 255)  # Ámbar
            draw_corner_rect(frame, (left, top), (right, bottom), color, thickness=2, line_length=20)
            
            cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 38), (30, 25, 20), -1)
            cv2.rectangle(frame, (left, bottom + 5), (right, bottom + 38), color, 1)
            
            bar_w = right - left - 12
            filled_w = int(bar_w * progress)
            cv2.rectangle(frame, (left + 6, bottom + 24), (left + 6 + bar_w, bottom + 30), (60, 60, 60), -1)
            cv2.rectangle(frame, (left + 6, bottom + 24), (left + 6 + filled_w, bottom + 30), color, -1)
            
            cv2.putText(frame, f"Registrando nuevo... {int(progress * 100)}%", (left + 6, bottom + 19), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # Banner inferior
    if service.active_banner and time.time() < service.active_banner["expires"]:
        banner = service.active_banner
        banner_color = (30, 140, 50) if banner["type"] == "success" else (140, 90, 30)
        
        banner_overlay = frame.copy()
        cv2.rectangle(banner_overlay, (0, h - 50), (w, h), banner_color, -1)
        cv2.addWeighted(banner_overlay, 0.85, frame, 0.15, 0, frame)
        cv2.putText(frame, banner["text"], (30, h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1, cv2.LINE_AA)

def main():
    print("=" * 60)
    print(" INICIANDO SISTEMA AUTONOMO DE RECONOCIMIENTO EN TIENDA")
    print("=" * 60)
    
    service = FaceService(tolerance=0.52, greeting_cooldown=60, min_confirm_frames=6)
    
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("[ERROR] No se pudo acceder a la webcam.")
        return

    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    process_this_frame = True
    cached_results = []
    fps_time = time.time()
    fps_counter = 0
    fps_display = "FPS: 0"

    print("[INFO] Cámara iniciada. Presiona 'q' para salir, 'r' para recargar.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("[ALERTA] No se pudo leer el frame de video.")
            break

        if process_this_frame:
            cached_results = service.procesar_frame(frame, process_detection=True)

        process_this_frame = not process_this_frame

        draw_hud(frame, service, cached_results)

        fps_counter += 1
        if time.time() - fps_time >= 1.0:
            fps_display = f"FPS: {fps_counter}"
            fps_counter = 0
            fps_time = time.time()
        cv2.putText(frame, fps_display, (frame.shape[1] - 110, 35), cv2.FONT_HERSHEY_DUPLEX, 0.5, (160, 160, 160), 1, cv2.LINE_AA)

        cv2.imshow("Reconocimiento Facial - Tienda", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('r'):
            service.recargar_clientes()
            service.set_banner("Clientes recargados desde la base de datos.", duration=2.5, banner_type="info")

    video_capture.release()
    cv2.destroyAllWindows()
    print("[INFO] Sistema finalizado correctamente.")

if __name__ == "__main__":
    main()
