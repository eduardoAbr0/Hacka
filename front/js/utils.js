// Utilidades compartidas entre páginas

const IMAGEN_POR_DEFECTO =
    "data:image/svg+xml;utf8," +
    encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3"><rect width="4" height="3" fill="#e9ecef"/></svg>');

function formatearPrecio(precio) {
    return precio.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

// Pone nombre y logo del negocio en la barra superior
function iniciarBarraSuperior() {
    document.getElementById("nombre-negocio").textContent = NEGOCIO.nombre;
    document.getElementById("logo-negocio").src = NEGOCIO.logo;
}
