"""
API web del módulo de recomendaciones (ver guia_desarrollador_web.md).

Ejecutar:
    python -m uvicorn api_web:app --reload
Luego abrir:
    http://127.0.0.1:8000/?cliente=1
"""
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ml_recommender import RecomendadorProductos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Tienda - Recomendaciones")
recomendador = RecomendadorProductos()

# Permite abrir front/index.html desde otro servidor (Live Server, file://, etc.)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


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


# La web se sirve desde la misma dirección que la API
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "front"), html=True), name="front")
