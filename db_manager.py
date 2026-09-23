import sqlite3
import datetime
import os
import json
import contextlib
import numpy as np

try:
    import sqlitecloud
    SQLITE_CLOUD_AVAILABLE = True
except ImportError:
    SQLITE_CLOUD_AVAILABLE = False

DB_NAME = "tienda.db"
CONFIG_FILE = "cloud_config.json"

class DatabaseManager:
    def __init__(self, db_path=None, cloud_url=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, CONFIG_FILE)
        
        # 1. Prioridad: Parámetro explícito -> Archivo de configuración -> Variable de entorno -> SQLite local
        self.cloud_url = cloud_url or self._cargar_cloud_url()
        
        if db_path is None:
            self.db_path = os.path.join(base_dir, DB_NAME)
        else:
            self.db_path = db_path
            
        if self.cloud_url and SQLITE_CLOUD_AVAILABLE:
            print(f"[DB] Conectado a SQLite Cloud en la nube.")
        else:
            print(f"[DB] Usando base de datos local SQLite: {self.db_path}")

        self.init_db()

    def _cargar_cloud_url(self):
        """Carga el connection string de SQLite Cloud desde cloud_config.json o variable de entorno."""
        env_url = os.environ.get("SQLITE_CLOUD_URL")
        if env_url:
            return env_url
            
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg.get("sqlite_cloud_url", "").strip() or None
            except Exception:
                pass
        return None

    def guardar_cloud_url(self, url):
        """Guarda el connection string en cloud_config.json para persistencia."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"sqlite_cloud_url": url.strip()}, f, indent=2)
        self.cloud_url = url.strip()
        print(f"[DB] Configuración de SQLite Cloud actualizada.")

    @contextlib.contextmanager
    def get_connection(self):
        """Retorna conexión a SQLite Cloud si está configurada, o a SQLite local."""
        if self.cloud_url and SQLITE_CLOUD_AVAILABLE:
            conn = sqlitecloud.connect(self.cloud_url)
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 10000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Tabla de Clientes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    foto_path TEXT,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Tabla de Productos (códigos de barra y soporte API)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo_barras TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    categoria TEXT DEFAULT 'General',
                    precio REAL NOT NULL,
                    stock INTEGER DEFAULT 0,
                    origen TEXT DEFAULT 'local'
                )
            """)

            # 3. Tabla de Ventas (Cabecera de tickets)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente_id INTEGER NOT NULL,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total REAL DEFAULT 0.0,
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
                )
            """)

            # 4. Tabla Detalle de Ventas (Productos en cada ticket)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detalle_ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_id INTEGER NOT NULL,
                    producto_id INTEGER NOT NULL,
                    cantidad INTEGER DEFAULT 1,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT
                )
            """)

    # ==========================================
    # GESTIÓN DE CLIENTES
    # ==========================================

    def generar_siguiente_codigo(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clientes ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            next_id = 1 if row is None else row[0] + 1
            return f"CLI-{next_id:04d}"

    def registrar_cliente(self, codigo, nombre, encoding_np, foto_path):
        encoding_bytes = encoding_np.astype(np.float64).tobytes()
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clientes (codigo, nombre, encoding, foto_path, fecha_registro)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, nombre, encoding_bytes, foto_path, ahora))
            return cursor.lastrowid

    def cargar_clientes(self):
        """Carga clientes en memoria con estadísticas de compras."""
        clientes = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.codigo, c.nombre, c.encoding, c.foto_path, c.fecha_registro,
                       COUNT(v.id) AS num_compras,
                       COALESCE(SUM(v.total), 0.0) AS total_gastado
                FROM clientes c
                LEFT JOIN ventas v ON c.id = v.cliente_id
                GROUP BY c.id
            """)
            for row in cursor.fetchall():
                c_id, codigo, nombre, enc_bytes, foto_path, fecha_reg, num_compras, total_gastado = row
                encoding_np = np.frombuffer(enc_bytes, dtype=np.float64)
                clientes.append({
                    "id": c_id,
                    "codigo": codigo,
                    "nombre": nombre,
                    "encoding": encoding_np,
                    "foto_path": foto_path,
                    "fecha_registro": fecha_reg,
                    "total_compras": num_compras,
                    "total_gastado": float(total_gastado)
                })
        return clientes

    def actualizar_nombre_cliente(self, codigo, nuevo_nombre):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE clientes SET nombre = ? WHERE codigo = ?", (nuevo_nombre, codigo))
            return cursor.rowcount > 0

    def obtener_resumen_cliente(self, cliente_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(id), COALESCE(SUM(total), 0.0)
                FROM ventas
                WHERE cliente_id = ?
            """, (cliente_id,))
            row = cursor.fetchone()
            return {"total_compras": row[0], "total_gastado": float(row[1])}

    # ==========================================
    # GESTIÓN DE PRODUCTOS (CÓDIGOS DE BARRA / APIS)
    # ==========================================

    def crear_producto(self, codigo_barras, nombre, categoria="General", precio=0.0, stock=100, origen="local"):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO productos (codigo_barras, nombre, categoria, precio, stock, origen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(codigo_barras) DO UPDATE SET
                    nombre = excluded.nombre,
                    categoria = excluded.categoria,
                    precio = excluded.precio,
                    stock = excluded.stock,
                    origen = excluded.origen
            """, (str(codigo_barras).strip(), nombre, categoria, float(precio), int(stock), origen))
            return cursor.lastrowid

    def buscar_producto_por_codigo(self, codigo_barras):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, codigo_barras, nombre, categoria, precio, stock, origen
                FROM productos
                WHERE codigo_barras = ?
            """, (str(codigo_barras).strip(),))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0], "codigo_barras": row[1], "nombre": row[2],
                    "categoria": row[3], "precio": float(row[4]), "stock": row[5], "origen": row[6]
                }
            return None

    def listar_productos(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, codigo_barras, nombre, categoria, precio, stock, origen FROM productos ORDER BY categoria, nombre")
            filas = cursor.fetchall()
            return [{
                "id": r[0], "codigo_barras": r[1], "nombre": r[2],
                "categoria": r[3], "precio": float(r[4]), "stock": r[5], "origen": r[6]
            } for r in filas]

    def precargar_productos_ejemplo(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM productos")
            if cursor.fetchone()[0] == 0:
                ejemplos = [
                    ("7501055310884", "Coca-Cola Original 600ml", "Bebidas", 18.50, 50, "local"),
                    ("7501000111207", "Papas Sabritas Sal 45g", "Snacks", 22.00, 40, "local"),
                    ("7501030467145", "Agua Ciel Purificada 1L", "Bebidas", 14.00, 60, "local"),
                    ("7501000153108", "Galletas Emperador Chocolate 101g", "Snacks", 19.50, 35, "local"),
                    ("7501020512345", "Leche Lala Entera 1L", "Lacteos", 26.50, 30, "local"),
                    ("7501032300129", "Cafe Soluble Nescafe Clasico 120g", "Abarrotes", 68.00, 20, "local")
                ]
                cursor.executemany("""
                    INSERT INTO productos (codigo_barras, nombre, categoria, precio, stock, origen)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ejemplos)

    # ==========================================
    # GESTIÓN DE VENTAS
    # ==========================================

    def registrar_venta(self, cliente_id, items):
        if not items:
            raise ValueError("No se puede registrar una venta sin productos.")

        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO ventas (cliente_id, fecha, total) VALUES (?, ?, 0.0)", (cliente_id, ahora))
            venta_id = cursor.lastrowid
            
            total_venta = 0.0
            
            for item in items:
                if isinstance(item, dict):
                    p_id = item["producto_id"]
                    cant = item.get("cantidad", 1)
                else:
                    p_id, cant = item

                cursor.execute("SELECT precio, stock FROM productos WHERE id = ?", (p_id,))
                p_row = cursor.fetchone()
                if not p_row:
                    raise ValueError(f"Producto con ID {p_id} no existe.")

                precio_unitario, stock_actual = p_row
                subtotal = precio_unitario * cant
                total_venta += subtotal

                cursor.execute("""
                    INSERT INTO detalle_ventas (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (venta_id, p_id, cant, precio_unitario, subtotal))

                cursor.execute("UPDATE productos SET stock = MAX(0, stock - ?) WHERE id = ?", (cant, p_id))

            cursor.execute("UPDATE ventas SET total = ? WHERE id = ?", (total_venta, venta_id))
            return venta_id, total_venta

    def obtener_historial_ventas(self, limite=30):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.id, c.codigo, c.nombre, v.fecha, v.total,
                       COUNT(d.id) AS total_items
                FROM ventas v
                JOIN clientes c ON v.cliente_id = c.id
                LEFT JOIN detalle_ventas d ON v.id = d.venta_id
                GROUP BY v.id
                ORDER BY v.id DESC
                LIMIT ?
            """, (limite,))
            filas = cursor.fetchall()
            return [{
                "venta_id": r[0], "codigo": r[1], "cliente": r[2],
                "fecha": r[3], "total": float(r[4]), "num_items": r[5]
            } for r in filas]

    def obtener_detalle_venta(self, venta_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.codigo_barras, p.nombre, p.categoria, d.cantidad, d.precio_unitario, d.subtotal
                FROM detalle_ventas d
                JOIN productos p ON d.producto_id = p.id
                WHERE d.venta_id = ?
            """, (venta_id,))
            return cursor.fetchall()

    def contar_estadisticas(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clientes")
            total_c = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM productos")
            total_p = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(total), 0.0) FROM ventas")
            row_v = cursor.fetchone()
            total_v, total_ingresos = row_v[0], float(row_v[1])
            return {
                "clientes": total_c,
                "productos": total_p,
                "ventas": total_v,
                "ingresos": total_ingresos
            }

    # ==========================================
    # DATASETS PARA MACHINE LEARNING
    # ==========================================

    def obtener_dataset_cliente_producto(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT v.cliente_id, c.codigo, c.nombre AS cliente_nombre,
                       d.producto_id, p.nombre AS producto_nombre, p.categoria,
                       SUM(d.cantidad) AS frecuencia_compra,
                       SUM(d.subtotal) AS gasto_total
                FROM detalle_ventas d
                JOIN ventas v ON d.venta_id = v.id
                JOIN clientes c ON v.cliente_id = c.id
                JOIN productos p ON d.producto_id = p.id
                GROUP BY v.cliente_id, d.producto_id
                ORDER BY v.cliente_id, frecuencia_compra DESC
            """)
            filas = cursor.fetchall()
            return [{
                "cliente_id": r[0], "cliente_codigo": r[1], "cliente_nombre": r[2],
                "producto_id": r[3], "producto_nombre": r[4], "categoria": r[5],
                "frecuencia": r[6], "gasto_total": float(r[7])
            } for r in filas]

    def obtener_canastas_compras(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.venta_id, p.nombre
                FROM detalle_ventas d
                JOIN productos p ON d.producto_id = p.id
                ORDER BY d.venta_id
            """)
            canastas = {}
            for venta_id, producto_nombre in cursor.fetchall():
                canastas.setdefault(venta_id, []).append(producto_nombre)
            return list(canastas.values())
