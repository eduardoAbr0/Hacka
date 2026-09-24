import os
import sys
import time
import socket
import threading
import subprocess

def is_port_in_use(port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def run_web_server():
    if is_port_in_use(8000):
        print("[RUNNER] Servidor Web API ya está activo en http://127.0.0.1:8000")
        return
    print("[RUNNER] Iniciando Servidor Web API en http://127.0.0.1:8000 ...")
    subprocess.run([sys.executable, "-m", "uvicorn", "api_web:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"])

def run_foto_api_server():
    if is_port_in_use(3000):
        print("[RUNNER] API de Fotos / Escáner ESP32 ya está activo en el puerto 3000")
        return
    print("[RUNNER] Iniciando API de Fotos / Escáner ESP32 en puerto 3000 ...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_foto_path = os.path.join(base_dir, "APIs", "API_foto.py")
    subprocess.run([sys.executable, api_foto_path])

def main():
    print("=" * 65)
    print("        INICIANDO TIENDA INTELIGENTE EN TIEMPO REAL")
    print("=" * 65)
    print(" 1. Kiosco Web + Recomendaciones:       http://127.0.0.1:8000")
    print(" 2. Carrito de Compras:                 http://127.0.0.1:8000/ventas.html")
    print(" 3. Registro de Productos (Admin):      http://127.0.0.1:8000/productos.html")
    print(" 4. Cámara HD Escáner (Celular/ESP32):  http://127.0.0.1:3000/camara.html")
    print(" 5. Reconocimiento Facial Activo (Cámara Webcam integrada)")
    print(" Presiona Ctrl+C en la consola o 'q' en la webcam para detener.")
    print("=" * 65)

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    foto_thread = threading.Thread(target=run_foto_api_server, daemon=True)
    foto_thread.start()

    time.sleep(1.5)

    try:
        from store_app import main as camera_main
        camera_main()
    except Exception as e:
        print(f"[RUNNER] Aviso en Reconocimiento Facial (Webcam local): {e}")

    print("[RUNNER] Servidores activos en segundo plano. Presiona Ctrl+C para finalizar todo.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[RUNNER] Cerrando sistema completo...")

if __name__ == "__main__":
    main()
