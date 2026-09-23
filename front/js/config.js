// Datos del negocio (cambiar aquí el nombre y el logo)
const NEGOCIO = {
    nombre: "Mi Negocio",
    logo: "img/logo.svg"
};

// Conexión con la API de recomendaciones (api_web.py)
const API = {
    // Vacío = misma dirección que la página. Si abres el HTML por separado usa "http://127.0.0.1:8000"
    url: location.protocol === "file:" ? "http://127.0.0.1:8000" : "",
    // Cliente a mostrar si la URL no trae ?cliente=ID
    clientePorDefecto: 1,
    // Recomendaciones personales del cliente (panel "Sugerencias para ti")
    limitePersonal: 3,
    // Productos populares de la tienda (cartas; la cuadrícula es de 2 x 2)
    limiteGeneral: 4
};

// Ícono de respaldo por categoría (los productos no traen imagen)
const ICONOS_CATEGORIA = {
    Bebidas: "🥤",
    Snacks: "🍿",
    Lacteos: "🥛",
    Abarrotes: "🛒",
    General: "📦"
};
