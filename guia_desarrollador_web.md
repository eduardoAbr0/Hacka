# Guía de Integración: Módulo de Recomendaciones ML con Scikit-Learn

Esta guía está dirigida al **desarrollador web** para consumir de forma sencilla las recomendaciones de productos generadas mediante Machine Learning.

---

## 1. Archivos Requeridos para la Web
Asegúrate de tener en la raíz del proyecto web los siguientes archivos:
* **`ml_recommender.py`**: El motor de recomendación.
* **`modelo_recomendacion.joblib`**: El modelo pre-entrenado con Scikit-Learn.
* **`db_manager.py`**: El gestor de la base de datos (local o SQLite Cloud).

---

## 2. Uso Directo en Python (1 Línea de Código)

```python
from ml_recommender import RecomendadorProductos

# Inicializar el recomendador (carga automáticamente el modelo .joblib en milisegundos)
recomendador = RecomendadorProductos()

# Obtener las 3 mejores recomendaciones para el cliente con ID 1
recomendaciones = recomendador.obtener_recomendaciones(cliente_id=1, top_n=3)

print(recomendaciones)
```

---

## 3. Ejemplo de Estructura de Respuesta (JSON)

Cada elemento retornado por `obtener_recomendaciones()` tiene el siguiente formato estándar en Python `dict`:

```json
[
  {
    "producto_id": 1,
    "codigo_barras": "7501055310884",
    "nombre": "Coca-Cola Original 600ml",
    "categoria": "Bebidas",
    "precio": 18.50,
    "score": 4.601,
    "motivo": "Recomendado por clientes con patrones de compra similares"
  },
  {
    "producto_id": 2,
    "codigo_barras": "7501000111207",
    "nombre": "Papas Sabritas Sal 45g",
    "categoria": "Snacks",
    "precio": 22.00,
    "score": 3.756,
    "motivo": "Tu producto frecuente preferido"
  }
]
```

---

## 4. Ejemplo de Integración en FastAPI / Flask / Django

### Ejemplo con **FastAPI**:
```python
from fastapi import FastAPI
from ml_recommender import RecomendadorProductos

app = FastAPI()
recomendador = RecomendadorProductos()

@app.get("/api/recomendaciones/{cliente_id}")
def get_recomendaciones(cliente_id: int, limit: int = 3):
    return recomendador.obtener_recomendaciones(cliente_id=cliente_id, top_n=limit)
```

### Ejemplo con **Flask**:
```python
from flask import Flask, jsonify, request
from ml_recommender import RecomendadorProductos

app = Flask(__name__)
recomendador = RecomendadorProductos()

@app.route("/api/recomendaciones/<int:cliente_id>", methods=["GET"])
def get_recomendaciones(cliente_id):
    limit = int(request.args.get("limit", 3))
    data = recomendador.obtener_recomendaciones(cliente_id=cliente_id, top_n=limit)
    return jsonify(data)
```

---

## 5. Reentrenamiento Automático del Modelo
Si deseas reentrenar el modelo después de que ocurran nuevas ventas en la tienda:

```python
recomendador.entrenar_modelo()
```
Esto actualizará `modelo_recomendacion.joblib` con los nuevos patrones de compra.
