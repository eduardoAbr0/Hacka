// Utilidades compartidas entre páginas

const IMAGEN_POR_DEFECTO =
    "data:image/svg+xml;utf8," +
    encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 100 100"><rect width="100" height="100" fill="#f1f5f9"/><path d="M35 30 L65 30 L75 45 L75 75 A 5 5 0 0 1 70 80 L30 80 A 5 5 0 0 1 25 75 L25 45 Z" fill="none" stroke="#94a3b8" stroke-width="4" stroke-linejoin="round"/><path d="M25 45 L75 45" stroke="#94a3b8" stroke-width="4"/><path d="M42 30 A 8 8 0 0 1 58 30" fill="none" stroke="#94a3b8" stroke-width="4"/><text x="50" y="93" font-family="sans-serif" font-size="9" fill="#94a3b8" text-anchor="middle">Sin Imagen</text></svg>');

function formatearPrecio(precio) {
    return precio.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

// Pone nombre y logo del negocio en la barra superior
function iniciarBarraSuperior() {
    document.getElementById("nombre-negocio").textContent = NEGOCIO.nombre;
    document.getElementById("logo-negocio").src = NEGOCIO.logo;
}
