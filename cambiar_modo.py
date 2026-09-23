import os
import sys
import json
from db_manager import DatabaseManager

CONFIG_FILE = "cloud_config.json"
# URL guardada de tu clúster de SQLite Cloud para fácil conmutación
URL_NUBE_DEFAULT = "sqlitecloud://ca5bjhoxdz.g4.sqlite.cloud:8860/tienda.db?apikey=NBG4nU20gjD85pbuu1kgFsJYEilfXZEokZNG0iUo4mM"

def obtener_modo_actual():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, CONFIG_FILE)
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                url = cfg.get("sqlite_cloud_url", "").strip()
                if url:
                    return "NUBE", url
        except Exception:
            pass
    return "LOCAL", None

def cambiar_a_local():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, CONFIG_FILE)
    if os.path.exists(cfg_path):
        os.remove(cfg_path)
    print("\n" + "=" * 60)
    print(" [MODO ACTIVADO: LOCAL]")
    print(" El sistema ahora lee y escribe en:")
    print(f" {os.path.join(base_dir, 'tienda.db')}")
    print("=" * 60)

def cambiar_a_nube(url=None):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, CONFIG_FILE)
    target_url = url or URL_NUBE_DEFAULT
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump({"sqlite_cloud_url": target_url}, f, indent=2)
    print("\n" + "=" * 60)
    print(" [MODO ACTIVADO: NUBE (SQLite Cloud)]")
    print(f" URL: {target_url.split('?')[0]}?apikey=...")
    print("=" * 60)

def main():
    # Soporte para argumentos de consola: python cambiar_modo.py local / nube
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().strip()
        if arg in ("local", "1"):
            cambiar_a_local()
            return
        elif arg in ("nube", "cloud", "2"):
            cambiar_a_nube()
            return

    modo, url = obtener_modo_actual()
    print("=" * 60)
    print("        SELECTOR DE MODO: LOCAL vs NUBE")
    print("=" * 60)
    print(f"  Modo actual: [{modo}]")
    if modo == "NUBE":
        print(f"  Base remota: {url.split('?')[0]}")
    else:
        print("  Base local:  tienda.db (en este equipo)")
    print("-" * 60)
    print("  [1] Cambiar a LOCAL (tienda.db en disco)")
    print("  [2] Cambiar a NUBE (SQLite Cloud)")
    print("  [3] Salir")
    print("-" * 60)

    opc = input("Selecciona una opcion (1-3): ").strip()
    if opc == "1":
        cambiar_a_local()
    elif opc == "2":
        cambiar_a_nube()
    elif opc == "3":
        print("Sin cambios.")
    else:
        print("[!] Opcion no valida.")

if __name__ == "__main__":
    main()
