// Llamadas a la API de recomendaciones (api_web.py, ver guia_desarrollador_web.md).
// Los productos se adaptan al formato de cartas y modal:
// { id, nombre, descripcion, precio, imagen, razon, personalizado }

function imagenDeCategoria(categoria) {
    const icono = RECOMENDADOR.iconos[categoria] || RECOMENDADOR.iconos.General;
    return "data:image/svg+xml;utf8," + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">` +
        `<rect width="400" height="300" fill="#eef3ff"/>` +
        `<text x="200" y="150" font-size="120" text-anchor="middle" dominant-baseline="central">${icono}</text>` +
        `</svg>`
    );
}

function adaptarProducto(r) {
    return {
        id: r.producto_id,
        nombre: r.nombre,
        descripcion: r.categoria,
        precio: r.precio,
        imagen: r.imagen_url || r.imagen || imagenDeCategoria(r.categoria),
        razon: r.motivo,
        personalizado: r.personalizado !== false
    };
}

async function pedirJSON(ruta) {
    const resp = await fetch(`${RECOMENDADOR.url}${ruta}`);
    if (!resp.ok) throw new Error(`La API respondió ${resp.status}`);
    return resp.json();
}

const apiRecomendaciones = {
    // Solo las personales: si el modelo no conoce al cliente, la API devuelve populares
    async personales(clienteId) {
        const datos = await pedirJSON(`/api/recomendaciones/${clienteId}?limit=${RECOMENDADOR.limitePersonal}`);
        return datos.map(adaptarProducto).filter((p) => p.personalizado);
    },

    async populares() {
        const datos = await pedirJSON(`/api/populares?limit=${RECOMENDADOR.limiteGeneral}`);
        return datos.map(adaptarProducto);
    },

    // { estado: "idle" | "registrando" | "activo", cliente_id, mensaje }
    estadoCamara() {
        return pedirJSON("/api/camara/estado");
    }
};
