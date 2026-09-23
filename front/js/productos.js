// Obtiene los productos recomendados desde la API (ver guia_desarrollador_web.md)
// y los adapta al formato que usan las cartas y el modal:
// { id, nombre, descripcion, precio, imagen, razon }

function obtenerClienteId() {
    const id = Number(new URLSearchParams(location.search).get("cliente"));
    return Number.isInteger(id) && id > 0 ? id : API.clientePorDefecto;
}

function imagenDeCategoria(categoria) {
    const icono = ICONOS_CATEGORIA[categoria] || ICONOS_CATEGORIA.General;
    return "data:image/svg+xml;utf8," + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">` +
        `<rect width="400" height="300" fill="#eef3ff"/>` +
        `<text x="200" y="150" font-size="120" text-anchor="middle" dominant-baseline="central">${icono}</text>` +
        `</svg>`
    );
}

function adaptarRecomendacion(r) {
    return {
        id: r.producto_id,
        nombre: r.nombre,
        descripcion: r.categoria,
        precio: r.precio,
        imagen: imagenDeCategoria(r.categoria),
        razon: r.motivo,
        score: r.score,
        personalizado: r.personalizado !== false
    };
}

async function pedirProductos(ruta) {
    const resp = await fetch(`${API.url}${ruta}`);
    if (!resp.ok) throw new Error(`La API respondió ${resp.status}`);
    const datos = await resp.json();
    return datos.map(adaptarRecomendacion);
}

// Recomendaciones personales del cliente (panel lateral)
function obtenerRecomendaciones(clienteId, limite = API.limitePersonal) {
    return pedirProductos(`/api/recomendaciones/${clienteId}?limit=${limite}`);
}

// Productos populares para todos (cartas)
function obtenerPopulares(limite = API.limiteGeneral) {
    return pedirProductos(`/api/populares?limit=${limite}`);
}
