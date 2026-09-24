"""
API web de la tienda: recomendaciones (guia_desarrollador_web.md), estado de la cámara
e inventario de productos. También sirve las páginas de la carpeta front/.

Ejecutar:  python -m uvicorn api_web:app --reload   (o python run_tienda.py)
Abrir:     http://127.0.0.1:8000
"""
import os
import time
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ml_recommender import RecomendadorProductos
from db_manager import DatabaseManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.join(BASE_DIR, "front")

app = FastAPI(title="Tienda - Recomendaciones e Inventario")
recomendador = RecomendadorProductos()
db = DatabaseManager()

# Permite abrir el frontend desde cualquier servidor o puerto
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ==========================================
# ESTADO DE LA CÁMARA (lo envía face_service.py)
# ==========================================

SEGUNDOS_SIN_EVENTO = 15.0  # Mantiene activo al cliente 15s mientras escanea productos con el celular
MENSAJE_ESPERA = "Acércate a la cámara de la laptop para identificarte"

ESTADO_CAMARA = {
    "estado": "idle",
    "cliente_id": None,
    "codigo": None,
    "nombre": None,
    "mensaje": MENSAJE_ESPERA,
    "last_updated": time.time()
}


class EventoCamara(BaseModel):
    estado: str                         # "idle" | "registrando" | "activo" | "empleado" (trabajador)
    cliente_id: Optional[int] = None
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    mensaje: Optional[str] = None


@app.post("/api/camara/evento")
def recibir_evento_camara(evento: EventoCamara):
    nombre_cli = evento.nombre
    if evento.cliente_id and not nombre_cli:
        try:
            resumen = db.obtener_resumen_cliente(evento.cliente_id)
            if resumen:
                nombre_cli = resumen.get("nombre")
        except Exception:
            pass

    ESTADO_CAMARA.update(
        estado=evento.estado,
        cliente_id=evento.cliente_id,
        codigo=evento.codigo,
        nombre=nombre_cli,
        mensaje=evento.mensaje or "¡Hola de nuevo! 👋",
        last_updated=time.time()
    )
    return {"status": "ok"}


@app.get("/api/camara/estado")
def obtener_estado_camara():
    if time.time() - ESTADO_CAMARA["last_updated"] > SEGUNDOS_SIN_EVENTO:
        ESTADO_CAMARA.update(estado="idle", cliente_id=None, codigo=None, nombre=None, mensaje=MENSAJE_ESPERA)
    return ESTADO_CAMARA


# ==========================================
# RECOMENDACIONES
# ==========================================

@app.get("/api/recomendaciones/{cliente_id}")
def get_recomendaciones(cliente_id: int, limit: int = Query(3, ge=1, le=20)):
    datos = recomendador.obtener_recomendaciones(cliente_id=cliente_id, top_n=limit)
    # Si el modelo no conoce al cliente (sin compras) devuelve populares: no son personales
    conocido = cliente_id in getattr(recomendador, "user_to_idx", {})
    for r in datos:
        r["personalizado"] = conocido
    return datos


@app.get("/api/populares")
def get_populares(limit: int = Query(4, ge=1, le=20)):
    return recomendador._recomendar_mas_populares(top_n=limit, motivo="Es de los más vendidos de la tienda")


# ==========================================
# PRODUCTOS E INVENTARIO
# ==========================================

class ProductoSchema(BaseModel):
    codigo_barras: str
    nombre: str
    categoria: Optional[str] = "General"
    precio: float
    stock: Optional[int] = 50
    origen: Optional[str] = "local"
    imagen_url: Optional[str] = None


@app.get("/api/productos")
def listar_productos():
    return db.listar_productos()


@app.get("/api/productos/buscar/{codigo_barras}")
def buscar_producto_codigo(codigo_barras: str):
    prod = db.buscar_producto_por_codigo(codigo_barras)
    return {"existe": prod is not None, "producto": prod}


@app.post("/api/productos")
def crear_o_actualizar_producto(prod: ProductoSchema):
    if not prod.codigo_barras.strip():
        raise HTTPException(status_code=400, detail="El código de barras es obligatorio.")
    if not prod.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre del producto es obligatorio.")
    if prod.precio < 0:
        raise HTTPException(status_code=400, detail="El precio no puede ser negativo.")

    codigo = prod.codigo_barras.strip()
    db.crear_producto(
        codigo_barras=codigo,
        nombre=prod.nombre.strip(),
        categoria=prod.categoria.strip() if prod.categoria else "General",
        precio=prod.precio,
        stock=prod.stock or 50,
        origen=prod.origen or "local",
        imagen_url=prod.imagen_url.strip() if prod.imagen_url else None
    )

    # Se busca de nuevo porque lastrowid no da el id cuando el producto ya existía (upsert)
    guardado = db.buscar_producto_por_codigo(codigo)
    recomendador.productos_map[guardado["id"]] = guardado

    return {
        "status": "ok",
        "mensaje": f"Producto '{prod.nombre}' registrado con éxito.",
        "producto_id": guardado["id"]
    }


# ==========================================
# VENTAS Y REGISTRO DE TICKETS
# ==========================================

class ItemVentaSchema(BaseModel):
    producto_id: int
    cantidad: int = 1

class VentaSchema(BaseModel):
    cliente_id: int
    items: list[ItemVentaSchema]

@app.post("/api/ventas")
def registrar_venta(venta: VentaSchema):
    if not venta.cliente_id:
        raise HTTPException(status_code=400, detail="Se requiere identificación facial del cliente para realizar la compra.")
    if not venta.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío.")

    try:
        items_tuple = [(item.producto_id, item.cantidad) for item in venta.items]
        venta_id, total = db.registrar_venta(venta.cliente_id, items_tuple)

        try:
            recomendador.entrenar_modelo()
        except Exception:
            pass

        return {
            "status": "ok",
            "mensaje": f"¡Venta registrada con éxito! Ticket #{venta_id}",
            "venta_id": venta_id,
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# PÁGINAS (carpeta front/)
# ==========================================

@app.get("/productos")
def pagina_registro_productos():
    return FileResponse(os.path.join(FRONT_DIR, "productos.html"))


app.mount("/", StaticFiles(directory=FRONT_DIR, html=True), name="front")
