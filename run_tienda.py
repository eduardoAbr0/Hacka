import sys
import time
import threading
import subprocess

def run_web_server():
    print("[RUNNER] Iniciando Servidor Web API en http://127.0.0.1:8000 ...")
    subprocess.run([sys.executable, "-m", "uvicorn", "api_web:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"])

def main():
    print("=" * 65)
    print("        INICIANDO TIENDA INTELIGENTE EN TIEMPO REAL")
    print("=" * 65)
    print(" 1. Servidor Web + API ML: http://127.0.0.1:8000")
    print(" 2. Escáner de Cámara + Reconocimiento Facial Activo")
    print(" Presiona 'q' en la ventana de la cámara para finalizar.")
    print("=" * 65)

    # Iniciar servidor web en hilo secundario
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Esperar 2 segundos para asegurar que Uvicorn haya iniciado
    time.sleep(2.0)

    # Iniciar cámara en el hilo principal
    from store_app import main as camera_main
    try:
        camera_main()
    except KeyboardInterrupt:
        pass

    print("[RUNNER] Sistema cerrado correctamente.")

if __name__ == "__main__":
    main()
