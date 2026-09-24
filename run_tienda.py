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
    subprocess.run([sys.executable, "-m", "uvicorn", "api_web:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"])

def main():
    print("=" * 65)
    print("        INICIANDO TIENDA INTELIGENTE EN TIEMPO REAL")
    print("=" * 65)
    print(" 1. Servidor Web + API + Registro Productos: http://127.0.0.1:8000")
    print(" 2. Escáner de Cámara + Reconocimiento Facial Activo")
    print(" Presiona 'q' en la ventana de la cámara para finalizar.")
    print("=" * 65)

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    time.sleep(1.5)

    from store_app import main as camera_main
    try:
        camera_main()
    except KeyboardInterrupt:
        pass

    print("[RUNNER] Sistema cerrado correctamente.")

if __name__ == "__main__":
    main()
