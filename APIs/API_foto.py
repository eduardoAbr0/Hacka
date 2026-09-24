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
import sys
import socket
import threading
import urllib.request
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, abort, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_FOTOS = os.path.join(BASE, "fotos")
CARPETA_WEB = os.path.abspath(os.path.join(BASE, "..", "front"))
PUERTO = 3000                            # el ESP32 sube a http://<ip>:3000/api/upload
CAMPO_ARCHIVO = "file"                   # API_CAMPO en el código del ESP32
API_TOKEN = os.environ.get("API_TOKEN", "")
TAMANO_MAXIMO = 8 * 1024 * 1024          # 8 MB por foto
NOMBRE_VALIDO = re.compile(r"^[\w\-]+\.jpg$")

# Configuración de Cámara Celular (IP Webcam / DroidCam / Stream IP)
# Ejemplo IP Webcam: http://192.168.1.50:8080/shot.jpg
# Ejemplo DroidCam:  http://192.168.1.50:4747/cam/1/frame.jpg
CONFIG_CAMARA = {
    "ip_cam_url": os.environ.get("IP_CAM_URL", "http://10.32.0.62:8080/shot.jpg"),
    "usar_camara_celular": os.environ.get("USAR_CAMARA_CELULAR", "true").lower() in ("true", "1", "yes"),
    "timeout": 5
}

os.makedirs(CARPETA_FOTOS, exist_ok=True)

app = Flask(__name__, static_folder=CARPETA_WEB, static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = TAMANO_MAXIMO

# Conexión a la base de datos de la tienda
PADRE_DIR = os.path.abspath(os.path.join(BASE, ".."))
if PADRE_DIR not in sys.path:
    sys.path.insert(0, PADRE_DIR)

db = None
try:
    from db_manager import DatabaseManager
    db = DatabaseManager()
    db.precargar_productos_ejemplo()
    print("[API_foto] Base de datos conectada e inicializada.")
except Exception as e:
    print(f"[API_foto] Aviso de base de datos: {e}")

# Escáner de código de barras con soporte para espejo u orientaciones invertidas
def escanear_codigo_barras(datos_bytes):
    if not datos_bytes:
        return None, None
    
    nparr = np.frombuffer(datos_bytes, np.uint8)
    img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_original is None:
        return None, None

    # Orientaciones a probar por si la cámara manda efecto espejo o rotada
    orientaciones = [
        ("original", img_original),
        ("espejo_horizontal", cv2.flip(img_original, 1)),
        ("espejo_vertical", cv2.flip(img_original, 0)),
        ("rotado_180", cv2.rotate(img_original, cv2.ROTATE_180))
    ]

    # 1. Intentar con zxingcpp en todas las orientaciones
    try:
        import zxingcpp
        for nombre_ori, img in orientaciones:
            resultados = zxingcpp.read_barcodes(img)
            if resultados:
                codigo = resultados[0].text.strip()
                print(f"[BARCODE] Escaneado con zxingcpp ({nombre_ori}): {codigo}")
                return codigo, img
    except Exception:
        pass

    # 2. Respaldo con pyzbar si estuviera disponible
    try:
        from pyzbar.pyzbar import decode
        from PIL import Image
        import io
        for nombre_ori, img in orientaciones:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
            codigos = decode(pil_img)
            if codigos:
                codigo = codigos[0].data.decode("utf-8").strip()
                print(f"[BARCODE] Escaneado con pyzbar ({nombre_ori}): {codigo}")
                return codigo, img
    except Exception:
        pass

    # Si no leyó código, devolvemos la imagen corregida con espejo horizontal por defecto
    return None, cv2.flip(img_original, 1)

# Estado global
estado = {"ultima_subida": None, "ip_esp32": None, "ultimo_escaneo": None}
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
    return send_from_directory(CARPETA_WEB, "camara.html")


# ---------- API ----------
# ---------- Captura desde Cámara IP de Celular ----------
def obtener_foto_celular(url=None, timeout=None):
    """
    Obtiene una captura en alta resolución desde la app IP Webcam / DroidCam / Stream del smartphone.
    Intenta automáticamente varias rutas estándar (/shot.jpg, /photoaf.jpg, /cam/1/frame.jpg) si la URL no incluye la extensión.
    """
    base_url = url or CONFIG_CAMARA["ip_cam_url"]
    t_out = timeout or CONFIG_CAMARA.get("timeout", 5)

    if not base_url:
        return None, "URL de cámara celular no configurada."

    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "http://" + base_url

    base_url = base_url.rstrip("/")

    # Lista de posibles endpoints a probar si la URL base no trae una ruta de imagen específica
    urls_a_probar = [base_url]
    if not re.search(r"\.(jpg|jpeg|png)$", base_url, re.IGNORECASE):
        urls_a_probar.extend([
            f"{base_url}/shot.jpg",
            f"{base_url}/photoaf.jpg",
            f"{base_url}/photo.jpg",
            f"{base_url}/cam/1/frame.jpg",
        ])

    ultimo_error = ""

    for target_url in urls_a_probar:
        print(f"[CAMARA_CELULAR] Intentando obtener foto desde: {target_url}")
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=t_out) as respuesta:
                datos = respuesta.read()
                
                # Buscar encabezado y fin de JPEG en los datos recibidos (por si viene embebido en HTML o stream)
                inicio_jpg = datos.find(b"\xff\xd8")
                if inicio_jpg != -1:
                    fin_jpg = datos.find(b"\xff\xd9", inicio_jpg)
                    if fin_jpg != -1:
                        datos_jpg = datos[inicio_jpg : fin_jpg + 2]
                    else:
                        datos_jpg = datos[inicio_jpg:]

                    if len(datos_jpg) > 1000: # Mínimo 1 KB para una imagen real
                        print(f"[CAMARA_CELULAR] Foto HD recibida con éxito desde {target_url} ({len(datos_jpg) / 1024:.1f} KB)")
                        # Si una sub-ruta funcionó, actualizamos la configuración activa
                        CONFIG_CAMARA["ip_cam_url"] = target_url
                        return datos_jpg, None

                # Si es HTML o texto, extraer una pequeña muestra para diagnóstico
                snippet = datos[:100].decode("utf-8", errors="ignore").strip().replace("\n", " ")
                ultimo_error = f"La URL {target_url} devolvió texto/HTML en lugar de una imagen: '{snippet}'"
        except Exception as e:
            ultimo_error = f"Error al conectar a {target_url}: {e}"
            print(f"[CAMARA_CELULAR] {ultimo_error}")

    error_final = (
        f"{ultimo_error}. Asegúrate de que la app IP Webcam/DroidCam esté activa y que la URL "
        f"incluya '/shot.jpg' o '/cam/1/frame.jpg' (Ejemplo: http://192.168.1.50:8080/shot.jpg)."
    )
    return None, error_final


def procesar_y_guardar_imagen(datos, nombre_sugerido="foto", origen="desconocido"):
    if not datos or not datos.startswith(b"\xff\xd8"):
        return jsonify({"ok": False, "error": "El archivo no es una imagen JPEG válida"}), 415

    # Escaneo automático con corrección de orientaciones/espejo
    codigo, img_corregida = escanear_codigo_barras(datos)

    base = os.path.splitext(os.path.basename(nombre_sugerido))[0]
    base = re.sub(r"[^\w\-]", "", base) or "foto"
    nombre = f"{datetime.now():%Y%m%d_%H%M%S}_{origen}_{base}.jpg"

    # Guardar la imagen corregida
    ruta_guardado = os.path.join(CARPETA_FOTOS, nombre)
    if img_corregida is not None:
        cv2.imwrite(ruta_guardado, img_corregida)
    else:
        with open(ruta_guardado, "wb") as f:
            f.write(datos)

    producto_encontrado = None
    mensaje_escaneo = None
    tipo_escaneo = "sin_codigo"

    if codigo:
        if db:
            producto_encontrado = db.buscar_producto_por_codigo(codigo)

        if producto_encontrado:
            tipo_escaneo = "exito"
            mensaje_escaneo = f"Producto encontrado: {producto_encontrado['nombre']} (${producto_encontrado['precio']:.2f})"
            print(f"[API] 📦 {mensaje_escaneo} (Código: {codigo})")
        else:
            tipo_escaneo = "no_encontrado"
            mensaje_escaneo = f"No se encontró el producto en el inventario para el código: {codigo}"
            print(f"[API] ❌ {mensaje_escaneo}")
    else:
        tipo_escaneo = "sin_codigo"
        mensaje_escaneo = "No se detectó ningún código de barras en la foto recién capturada."
        print(f"[API] ℹ️ {mensaje_escaneo}")

    with candado:
        estado["ultima_subida"] = datetime.now().isoformat(timespec="seconds")
        estado["ip_esp32"] = request.remote_addr
        estado["ultimo_escaneo"] = {
            "tipo": tipo_escaneo,
            "codigo_barras": codigo,
            "producto": producto_encontrado,
            "mensaje": mensaje_escaneo,
            "origen": origen,
            "timestamp": datetime.now().isoformat(timespec="seconds")
        }

    print(f"[API] Foto procesada (Origen: {origen}): {nombre} ({len(datos) / 1024:.1f} KB)")
    return jsonify({
        "ok": True,
        "nombre": nombre,
        "url": f"/api/fotos/{nombre}",
        "tipo": tipo_escaneo,
        "codigo_barras": codigo,
        "producto": producto_encontrado,
        "mensaje": mensaje_escaneo,
        "origen": origen
    }), 201


# ---------- API ----------
@app.route("/api/trigger", methods=["GET", "POST"])
def api_trigger():
    """
    Disparador directo: la llamada solicita inmediatamente a la cámara del celular tomar una foto,
    escanea el código de barras y guarda la captura HD.
    Puede ser invocado por el ESP32 (cuando el sensor detecta <20 cm) o desde el cliente web.
    """
    datos_cel, err = obtener_foto_celular()
    if not datos_cel:
        return jsonify({"ok": False, "error": f"Error al tomar foto con celular: {err}"}), 502

    return procesar_y_guardar_imagen(datos_cel, nombre_sugerido="trigger_celular", origen="celular")


@app.post("/api/upload")
@app.post("/api/deteccion")
def api_upload():
    """
    Recibe la foto/notificación del ESP32.
    Si 'usar_camara_celular' está activado, la API intentará obtener una foto en HD desde la cámara del celular.
    Si la cámara del celular no responde, utiliza la foto enviada por el ESP32 como respaldo.
    """
    if not token_valido():
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    # Extraer datos enviados por el ESP32 si los hay
    archivo = request.files.get(CAMPO_ARCHIVO)
    if archivo:
        datos_esp32 = archivo.read()
        nombre_sd = archivo.filename or ""
    else:
        datos_esp32 = request.get_data()
        nombre_sd = ""

    # Si está habilitada la cámara del celular, intentamos obtener foto HD
    if CONFIG_CAMARA.get("usar_camara_celular"):
        datos_cel, err_cel = obtener_foto_celular()
        if datos_cel:
            print("[API] Utilizando captura HD obtenida de la cámara del celular.")
            return procesar_y_guardar_imagen(datos_cel, nombre_sugerido="celular", origen="celular")
        else:
            print(f"[API] Cámara del celular no disponible. Intentando respaldo ESP32: {err_cel}")

    # Fallback o uso directo de la cámara del ESP32
    if not datos_esp32:
        return jsonify({
            "ok": False,
            "error": "No se pudo obtener la foto de la cámara del celular ni llegó imagen desde el ESP32."
        }), 400

    if not datos_esp32.startswith(b"\xff\xd8"):
        return jsonify({"ok": False, "error": "El archivo recibido del ESP32 no es un JPEG"}), 415

    return procesar_y_guardar_imagen(datos_esp32, nombre_sugerido=nombre_sd or "esp32", origen="esp32")


@app.route("/api/config_camara", methods=["GET", "POST"])
def api_config_camara():
    """Permite consultar o cambiar la IP/URL de la cámara del celular en tiempo de ejecución."""
    if request.method == "POST":
        req_data = request.get_json(silent=True) or request.form
        if "ip_cam_url" in req_data:
            CONFIG_CAMARA["ip_cam_url"] = req_data["ip_cam_url"].strip()
        if "usar_camara_celular" in req_data:
            val = str(req_data["usar_camara_celular"]).lower()
            CONFIG_CAMARA["usar_camara_celular"] = val in ("true", "1", "yes")

    return jsonify({
        "ok": True,
        "ip_cam_url": CONFIG_CAMARA["ip_cam_url"],
        "usar_camara_celular": CONFIG_CAMARA["usar_camara_celular"],
        "timeout": CONFIG_CAMARA["timeout"]
    })


# ---------- Proxies para conectar index.html con api_web.py (puerto 8000) ----------
@app.get("/api/camara/estado")
def proxy_camara_estado():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/camara/estado", timeout=2) as resp:
            return resp.read(), 200, {"Content-Type": "application/json"}
    except Exception:
        return jsonify({"estado": "idle", "cliente_id": None, "mensaje": "Esperando cliente"}), 200


@app.get("/api/populares")
def proxy_populares():
    try:
        limit = request.args.get("limit", 4)
        with urllib.request.urlopen(f"http://127.0.0.1:8000/api/populares?limit={limit}", timeout=2) as resp:
            return resp.read(), 200, {"Content-Type": "application/json"}
    except Exception:
        return jsonify([]), 200


@app.get("/api/recomendaciones/<int:cliente_id>")
def proxy_recomendaciones(cliente_id):
    try:
        limit = request.args.get("limit", 3)
        with urllib.request.urlopen(f"http://127.0.0.1:8000/api/recomendaciones/{cliente_id}?limit={limit}", timeout=2) as resp:
            return resp.read(), 200, {"Content-Type": "application/json"}
    except Exception:
        return jsonify([]), 200


@app.get("/api/estado")
def api_estado():
    return jsonify({
        "ok": True,
        "ultima_subida": estado["ultima_subida"],
        "ip_esp32": estado["ip_esp32"],
        "total_fotos": len(listar_fotos()),
        "ultimo_escaneo": estado.get("ultimo_escaneo"),
        "config_camara": CONFIG_CAMARA
    })


@app.get("/api/productos")
def api_listar_productos():
    if not db:
        return jsonify([])
    return jsonify(db.listar_productos())


@app.get("/api/productos/<codigo_barras>")
def api_obtener_producto(codigo_barras):
    if not db:
        abort(500, description="Base de datos no disponible")
    p = db.buscar_producto_por_codigo(codigo_barras)
    if not p:
        abort(404, description="Producto no encontrado")
    return jsonify(p)


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
    print("  API de fotos lista (Modo Híbrido: ESP32 + Cámara Smartphone)")
    print(f"  Página web:          http://{ip}:{PUERTO}/camara.html")
    print(f"  Endpoint ESP32:      http://{ip}:{PUERTO}/api/upload")
    print(f"  Endpoint Trigger:    http://{ip}:{PUERTO}/api/trigger")
    print(f"  Cámara Celular (IP): {CONFIG_CAMARA['ip_cam_url']}")
    print(f"  Usar Cámara Celular: {'Sí' if CONFIG_CAMARA['usar_camara_celular'] else 'No'}")
    print(f"  Token:               {'activado' if API_TOKEN else 'desactivado'}")
    print(f"  Fotos guardadas en:  {CARPETA_FOTOS}")
    print("=" * 64)
    app.run(host="0.0.0.0", port=PUERTO, threaded=True)
