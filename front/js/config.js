// Datos del negocio (cambiar aquí el nombre y el logo)
const NEGOCIO = {
    nombre: "Mi Negocio",
    logo: "img/logo.svg"
};

// API de recomendaciones y cámara (api_web.py) — usada por index.html
const RECOMENDADOR = {
    // Vacío = misma dirección que la página. Si abres el HTML como archivo, usa el puerto 8000
    url: location.protocol === "file:" ? "http://127.0.0.1:8000" : "",
    limitePersonal: 3,          // panel "Sugerencias para ti"
    limiteGeneral: 4,           // cartas "Lo más vendido" (cuadrícula 2 x 2)
    intervaloCamaraMs: 500,     // cada cuánto se revisa si hay cliente frente a la cámara
    // Ícono por categoría (los productos no traen imagen)
    iconos: { Bebidas: "🥤", Snacks: "🍿", Lacteos: "🥛", Abarrotes: "🛒", General: "📦" }
};

// Dirección de la API de fotos (API_foto.py)
const API_URL = (location.hostname && location.port === "3000") 
    ? "" 
    : `http://${location.hostname || "localhost"}:3000`;
