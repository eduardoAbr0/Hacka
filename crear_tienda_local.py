import os
import shutil
import sqlite3

def crear_base_local():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "tienda.db")
    schema_path = os.path.join(base_dir, "schema.sql")
    cloud_config_path = os.path.join(base_dir, "cloud_config.json")
    faces_dir = os.path.join(base_dir, "data", "clientes")
    faces_backup = os.path.join(base_dir, "data", "clientes_backup")

    print("=" * 65)
    print("      CREADOR DE BASE DE DATOS LOCAL: tienda.db")
    print("=" * 65)

    # 1. Desactivar conexion a la nube para volver a modo local
    if os.path.exists(cloud_config_path):
        os.remove(cloud_config_path)
        print("[OK] Modo nube desactivado. El sistema usara la base local en disco.")

    # 2. Respaldar fotos anteriores si existen
    if os.path.exists(faces_dir) and os.listdir(faces_dir):
        os.makedirs(faces_backup, exist_ok=True)
        for f in os.listdir(faces_dir):
            src = os.path.join(faces_dir, f)
            dst = os.path.join(faces_backup, f)
            shutil.copy2(src, dst)
        shutil.rmtree(faces_dir)
        print(f"[OK] Fotos anteriores respaldadas en: {faces_backup}")
    os.makedirs(faces_dir, exist_ok=True)

    # 3. Eliminar archivo tienda.db anterior si existe
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print("[OK] Archivo tienda.db anterior eliminado.")
        except Exception as e:
            print(f"[AVISO] No se pudo eliminar tienda.db directamente ({e}). Se sobreescribiran las tablas.")

    # 4. Crear estructura desde schema.sql
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_schema = f.read()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(sql_schema)
    
    # 5. Insertar productos de ejemplo
    ejemplos = [
        ("7501055310884", "Coca-Cola Original 600ml", "Bebidas", 18.50, 50, "local"),
        ("7501000111207", "Papas Sabritas Sal 45g", "Snacks", 22.00, 40, "local"),
        ("7501030467145", "Agua Ciel Purificada 1L", "Bebidas", 14.00, 60, "local"),
        ("7501000153108", "Galletas Emperador Chocolate 101g", "Snacks", 19.50, 35, "local"),
        ("7501020512345", "Leche Lala Entera 1L", "Lacteos", 26.50, 30, "local"),
        ("7501032300129", "Cafe Soluble Nescafe Clasico 120g", "Abarrotes", 68.00, 20, "local")
    ]
    conn.executemany("""
        INSERT INTO productos (codigo_barras, nombre, categoria, precio, stock, origen)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ejemplos)
    conn.commit()

    # 6. Validar estado
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM clientes")
    num_clientes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM productos")
    num_productos = cur.fetchone()[0]
    conn.close()

    print("\n" + "=" * 65)
    print(f" [EXITO] Nueva base de datos local creada en:")
    print(f" {db_path}")
    print(f"- Clientes iniciales: {num_clientes} (en limpio, listo para CLI-0001)")
    print(f"- Productos en inventario: {num_productos} (con codigos de barra)")
    print("=" * 65)

if __name__ == "__main__":
    crear_base_local()
