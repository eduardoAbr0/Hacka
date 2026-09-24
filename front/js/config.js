// Datos del negocio (cambiar aquí el nombre y el logo)
const NEGOCIO = {
    nombre: "Mi Negocio",
    logo: "img/logo.svg"
};

// Dirección de la API de fotos (API_foto.py).
// Si la página la sirve la propia API se usa la misma dirección;
// si se abre como archivo, se usa localhost.
const API_URL = location.protocol.startsWith("http") ? "" : "http://localhost:3000";
