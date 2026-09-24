// Llamadas a la API de recomendaciones (api_web.py, ver guia_desarrollador_web.md).
// Los productos se adaptan al formato de cartas y modal:
// { id, nombre, descripcion, precio, imagen, razon, personalizado }

// Imagen de relleno (los productos no traen imagen): bolsa sólida + nombre de la categoría
function imagenDeCategoria(categoria) {
    const texto = String(categoria || "Producto").replace(/[<>&"]/g, "");
    return "data:image/svg+xml;utf8," + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">` +
        `<rect width="400" height="300" fill="#eef1f6"/>` +
        `<path d="M165 110h70l-8 72h-54z" fill="#1B396A"/>` +
        `<path d="M183 110a17 17 0 0 1 34 0" fill="none" stroke="#1B396A" stroke-width="9" stroke-linecap="round"/>` +
        `<text x="200" y="222" font-family="Montserrat, sans-serif" font-size="20" font-weight="600" fill="#807E82" text-anchor="middle">${texto}</text>` +
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
