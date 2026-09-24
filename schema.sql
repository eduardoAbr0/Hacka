-- ========================================================
-- ESQUEMA DE BASE DE DATOS: TIENDA INTELIGENTE (tienda.db)
-- Soporta: Reconocimiento Facial, Códigos de Barra y ML
-- ========================================================

PRAGMA foreign_keys = ON;

-- 1. CLIENTES (Reconocimiento Facial y Datos)
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,             -- Ej: CLI-0001
    nombre TEXT NOT NULL,                    -- Nombre del cliente
    encoding BLOB NOT NULL,                  -- Vector facial de 128 floats
    foto_path TEXT,                          -- Ruta local de la foto
    foto_blob BLOB,                          -- Imagen JPG comprimida en binario
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo TEXT DEFAULT 'cliente',             -- 'cliente' o 'trabajador' (informativo)
    es_trabajador INTEGER DEFAULT 0          -- 1 = trabajador (la web le pide registrar su huella), otro = cliente
);

-- 2. PRODUCTOS (Inventario y Lector de Códigos de Barra / API)
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT UNIQUE NOT NULL,      -- Código EAN-13 / UPC
    nombre TEXT NOT NULL,                    -- Nombre del producto
    categoria TEXT DEFAULT 'General',        -- Para modelos de recomendación
    precio REAL NOT NULL,                    -- Precio unitario
    stock INTEGER DEFAULT 0,                 -- Unidades disponibles
    origen TEXT DEFAULT 'local'              -- 'local' o 'api'
);

-- 3. VENTAS (Cabecera de Ticket)
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,             -- Cliente que compró
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total REAL DEFAULT 0.0,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
);

-- 4. DETALLE_VENTAS (Productos en cada Ticket)
CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER DEFAULT 1,
    precio_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT
);

