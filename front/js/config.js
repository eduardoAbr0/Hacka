// Datos del negocio (cambiar aquí el nombre y el logo)
const NEGOCIO = {
    nombre: "Mi Negocio",
    logo: "img/logo.svg"
};

// Dirección de la API de fotos (API_foto.py)
const API_URL = (location.hostname && location.port === "3000") 
    ? "" 
    : `http://${location.hostname || "localhost"}:3000`;
