"""
API de fotos para el ESP32-S3 CAM (Freenove) con sensor ultrasónico.

Flujo:
  1. El sensor detecta un objeto a menos de 20 cm
  2. El ESP32 toma la foto, la guarda en su MicroSD y la sube  ->  POST /api/upload  (multipart, campo "file")
  3. La página muestra la foto                                 ->  GET  /api/fotos/ultima

Además sirve la carpeta app_web, así que la página se abre en http://<ip-de-la-pc>:3000/camara.html

Ejecutar:
    pip install -r requirements.txt
    python API_foto.py

Token opcional: si se define la variable de entorno API_TOKEN, el ESP32 debe mandar
"Authorization: Bearer <token>" (es el API_TOKEN del código del ESP32).
"""

import os
import re
import socket
import threading
from datetime import datetime

from flask import Flask, abort, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_FOTOS = os.path.join(BASE, "fotos")
CARPETA_WEB = os.path.join(BASE, "app_web")
PUERTO = 3000                            # el ESP32 sube a http://<ip>:3000/api/upload
CAMPO_ARCHIVO = "file"                   # API_CAMPO en el código del ESP32
API_TOKEN = os.environ.get("API_TOKEN", "")
TAMANO_MAXIMO = 8 * 1024 * 1024          # 8 MB por foto
NOMBRE_VALIDO = re.compile(r"^[\w\-]+\.jpg$")

os.makedirs(CARPETA_FOTOS, exist_ok=True)

app = Flask(__name__, static_folder=CARPETA_WEB, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = TAMANO_MAXIMO

# Última vez que el ESP32 subió algo
estado = {"ultima_subida": None, "ip_esp32": None}
candado = threading.Lock()


# ---------- CORS: permite llamar a la API desde la página aunque se abra como archivo ----------
@app.after_request
def agregar_cors(respuesta):
    respuesta.headers["Access-Control-Allow-Origin"] = "*"
    respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return respuesta


# ---------- Utilidades ----------
def listar_fotos():
    """Fotos ordenadas de la más nueva a la más vieja."""
    fotos = []
    for nombre in os.listdir(CARPETA_FOTOS):
        if not NOMBRE_VALIDO.match(nombre):
            continue
        info = os.stat(os.path.join(CARPETA_FOTOS, nombre))
        fotos.append({
            "nombre": nombre,
            "tamano": info.st_size,
            "fecha": datetime.fromtimestamp(info.st_mtime).isoformat(timespec="seconds"),
            "url": f"/api/fotos/{nombre}",
        })
    fotos.sort(key=lambda f: (f["fecha"], f["nombre"]), reverse=True)
    return fotos


def validar_nombre(nombre):
    if not NOMBRE_VALIDO.match(nombre):
        abort(400, description="Nombre de foto inválido")
    return nombre


def token_valido():
    return not API_TOKEN or request.headers.get("Authorization") == f"Bearer {API_TOKEN}"


# ---------- Página web ----------
@app.get("/")
def inicio():
    return send_from_directory(CARPETA_WEB, "index.html")


# ---------- API ----------
@app.post("/api/upload")
def api_upload():
    """
    Recibe la foto del ESP32 como multipart/form-data (campo "file", filename "foto_<millis>.jpg").
    También acepta el JPEG como cuerpo crudo (Content-Type: image/jpeg).
    """
    if not token_valido():
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    archivo = request.files.get(CAMPO_ARCHIVO)
    if archivo:
        datos = archivo.read()
        nombre_sd = archivo.filename or ""
    else:
        datos = request.get_data()
        nombre_sd = ""

    if not datos:
        return jsonify({"ok": False, "error": f"No llegó ninguna imagen en el campo '{CAMPO_ARCHIVO}'"}), 400
    if not datos.startswith(b"\xff\xd8"):
        return jsonify({"ok": False, "error": "El archivo no es un JPEG"}), 415

    # Se antepone fecha y hora porque el ESP32 usa millis() y el nombre se repite al reiniciar
    base = os.path.splitext(os.path.basename(nombre_sd))[0]
    base = re.sub(r"[^\w\-]", "", base) or "foto"
    nombre = f"{datetime.now():%Y%m%d_%H%M%S}_{base}.jpg"

    with open(os.path.join(CARPETA_FOTOS, nombre), "wb") as f:
        f.write(datos)

    with candado:
        estado["ultima_subida"] = datetime.now().isoformat(timespec="seconds")
        estado["ip_esp32"] = request.remote_addr

    print(f"[API] Foto recibida de {request.remote_addr}: {nombre} ({len(datos) / 1024:.1f} KB)")
    return jsonify({"ok": True, "nombre": nombre, "url": f"/api/fotos/{nombre}"}), 201


@app.get("/api/estado")
def api_estado():
    return jsonify({
        "ok": True,
        "ultima_subida": estado["ultima_subida"],
        "ip_esp32": estado["ip_esp32"],
        "total_fotos": len(listar_fotos()),
    })


@app.get("/api/fotos")
def api_listar_fotos():
    return jsonify(listar_fotos())


@app.get("/api/fotos/ultima")
def api_ultima_foto():
    fotos = listar_fotos()
    if not fotos:
        abort(404, description="Todavía no hay fotos")
    respuesta = send_from_directory(CARPETA_FOTOS, fotos[0]["nombre"], mimetype="image/jpeg")
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@app.get("/api/fotos/<nombre>")
def api_obtener_foto(nombre):
    return send_from_directory(CARPETA_FOTOS, validar_nombre(nombre), mimetype="image/jpeg")


@app.delete("/api/fotos/<nombre>")
def api_borrar_foto(nombre):
    ruta = os.path.join(CARPETA_FOTOS, validar_nombre(nombre))
    if not os.path.exists(ruta):
        abort(404, description="La foto no existe")
    os.remove(ruta)
    return jsonify({"ok": True})


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(413)
def error_json(e):
    return jsonify({"ok": False, "error": e.description}), e.code


# ---------- Inicio ----------
def ip_local():
    """IP de esta PC en la red WiFi (la que se pone en el ESP32)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    ip = ip_local()
    print("=" * 64)
    print("  API de fotos lista")
    print(f"  Pagina web:       http://{ip}:{PUERTO}/camara.html")
    print(f"  En el ESP32 pon:  API_URL = \"http://{ip}:{PUERTO}/api/upload\"")
    print(f"  Token:            {'activado' if API_TOKEN else 'desactivado (API_TOKEN vacio)'}")
    print(f"  Fotos guardadas en: {CARPETA_FOTOS}")
    print("=" * 64)
    app.run(host="0.0.0.0", port=PUERTO, threaded=True)
