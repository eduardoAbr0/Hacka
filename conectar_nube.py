import sys
import os
import sqlitecloud
from db_manager import DatabaseManager

def main():
    print("=" * 65)
    print("      CONFIGURADOR DE CONEXION A SQLITE CLOUD")
    print("=" * 65)
    print("\nPara conectar este sistema a tu base de datos en la nube:")
    print("1. Ve a tu consola en https://sqlitecloud.io")
    print("2. Abre tu proyecto/cluster y ve a la seccion 'Connect'")
    print("3. Copia el 'Connection String', que luce asi:")
    print("   sqlitecloud://xxxx.sqlite.cloud:8860/nombre_bd?apikey=yyyyyy\n")
    
    url = input("Pega tu Connection String aqui: ").strip()
    
    if not url:
        print("[!] No se ingreso ninguna URL. Cancelando.")
        return

    if not url.startswith("sqlitecloud://"):
        print("[!] La URL debe comenzar con 'sqlitecloud://'")
        return

    print("\nProbando conexion con SQLite Cloud...")
    try:
        conn = sqlitecloud.connect(url)
        cur = conn.cursor()
        cur.execute("SELECT sqlite_version()")
        version = cur.fetchone()[0]
        print(f"[OK] Conexion exitosa con SQLite Cloud (SQLite v{version})")
        conn.close()

        # Guardar en cloud_config.json
        db = DatabaseManager(cloud_url=url)
        db.guardar_cloud_url(url)
        
        # Inicializar tablas en la nube
        print("Sincronizando estructura de tablas en la nube...")
        db.init_db()
        db.precargar_productos_ejemplo()
        
        print("\n" + "=" * 65)
        print(" [EXITO] Tu sistema ahora esta conectado a SQLite Cloud.")
        print(" Todos los clientes, fotos y ventas se guardaran en la nube.")
        print("=" * 65)
        
    except Exception as e:
        print(f"\n[ERROR] No se pudo conectar a SQLite Cloud: {e}")
        print("Verifica que el API Key y el host sean correctos.")

if __name__ == "__main__":
    main()
