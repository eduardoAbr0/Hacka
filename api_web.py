import os
import time
import socket
from typing import Optional
from pydantic import BaseModel

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ml_recommender import RecomendadorProductos
from db_manager import DatabaseManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Tienda - Recomendaciones e Inventario")
recomendador = RecomendadorProductos()
db = DatabaseManager()

# Permite abrir el frontend desde cualquier servidor o puerto
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Estado global del escáner de cámara en tiempo real
ESTADO_CAMARA = {
    "estado": "idle",
    "cliente_id": None,
    "codigo": None,
    "mensaje": "Acércate a la cámara para ver tus sugerencias",
    "last_updated": time.time()
}

class EventoCamara(BaseModel):
    estado: str
    cliente_id: Optional[int] = None
    codigo: Optional[str] = None
    mensaje: Optional[str] = None

class ProductoSchema(BaseModel):
    codigo_barras: str
    nombre: str
    categoria: Optional[str] = "General"
    precio: float
    stock: Optional[int] = 50
    origen: Optional[str] = "local"


@app.post("/api/camara/evento")
def recibir_evento_camara(evento: EventoCamara):
    global ESTADO_CAMARA
    ESTADO_CAMARA["estado"] = evento.estado
    ESTADO_CAMARA["cliente_id"] = evento.cliente_id
    ESTADO_CAMARA["codigo"] = evento.codigo
    ESTADO_CAMARA["mensaje"] = evento.mensaje or "¡Hola de nuevo! 👋"
    ESTADO_CAMARA["last_updated"] = time.time()
    return {"status": "ok"}

@app.get("/api/camara/estado")
def obtener_estado_camara():
    if time.time() - ESTADO_CAMARA["last_updated"] > 4.0:
        ESTADO_CAMARA["estado"] = "idle"
        ESTADO_CAMARA["cliente_id"] = None
        ESTADO_CAMARA["codigo"] = None
        ESTADO_CAMARA["mensaje"] = "Acércate a la cámara para ver tus sugerencias"
    return ESTADO_CAMARA

@app.get("/api/recomendaciones/{cliente_id}")
def get_recomendaciones(cliente_id: int, limit: int = Query(3, ge=1, le=20)):
    datos = recomendador.obtener_recomendaciones(cliente_id=cliente_id, top_n=limit)
    conocido = cliente_id in getattr(recomendador, "user_to_idx", {})
    for r in datos:
        r["personalizado"] = conocido
    return datos

@app.get("/api/populares")
def get_populares(limit: int = Query(4, ge=1, le=20)):
    return recomendador._recomendar_mas_populares(top_n=limit, motivo="Es de los más vendidos de la tienda")

# ==========================================
# ENDPOINTS DE GESTIÓN DE PRODUCTOS E INVENTARIO
# ==========================================

@app.get("/api/productos")
def listar_productos():
    return db.listar_productos()

@app.get("/api/productos/buscar/{codigo_barras}")
def buscar_producto_codigo(codigo_barras: str):
    prod = db.buscar_producto_por_codigo(codigo_barras)
    if prod:
        return {"existe": True, "producto": prod}
    return {"existe": False, "producto": None}

@app.post("/api/productos")
def crear_o_actualizar_producto(prod: ProductoSchema):
    if not prod.codigo_barras.strip():
        raise HTTPException(status_code=400, detail="El código de barras es obligatorio.")
    if not prod.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre del producto es obligatorio.")
    if prod.precio < 0:
        raise HTTPException(status_code=400, detail="El precio no puede ser negativo.")

    p_id = db.crear_producto(
        codigo_barras=prod.codigo_barras.strip(),
        nombre=prod.nombre.strip(),
        categoria=prod.categoria.strip() if prod.categoria else "General",
        precio=prod.precio,
        stock=prod.stock or 50,
        origen=prod.origen or "local"
    )

    # Actualizar lista de productos en memoria del recomendador
    recomendador.productos_map[p_id] = db.buscar_producto_por_codigo(prod.codigo_barras)

    return {
        "status": "ok",
        "mensaje": f"Producto '{prod.nombre}' registrado con éxito.",
        "producto_id": p_id
    }

from fastapi.responses import FileResponse

@app.get("/productos")
def pagina_registro_productos():
    return FileResponse(os.path.join(BASE_DIR, "front", "productos.html"))

# Servir archivos estáticos del frontend
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "front"), html=True), name="front")
