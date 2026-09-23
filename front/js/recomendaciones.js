// Lógica del panel de recomendaciones (lista de burbujas)

function agregarRecomendacion(contenedor, texto, titulo = "") {
    const item = document.createElement("div");
    item.className = "recomendacion";

    if (titulo) {
        const t = document.createElement("strong");
        t.className = "recomendacion-titulo";
        t.textContent = titulo;
        item.appendChild(t);
    }
    const p = document.createElement("p");
    p.textContent = texto;
    item.appendChild(p);

    contenedor.appendChild(item);
    contenedor.scrollTop = contenedor.scrollHeight;
}

// Burbuja con un producto recomendado; al pulsarla se abre el modal
function agregarProductoRecomendado(contenedor, producto) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "recomendacion recomendacion-producto";
    item.dataset.id = producto.id;

    item.innerHTML = `
        <img class="recomendacion-imagen" alt="">
        <span class="recomendacion-info">
            <strong class="recomendacion-titulo"></strong>
            <span class="recomendacion-precio"></span>
            <span class="recomendacion-motivo"></span>
        </span>
    `;
    item.querySelector(".recomendacion-imagen").src = producto.imagen || IMAGEN_POR_DEFECTO;
    item.querySelector(".recomendacion-titulo").textContent = producto.nombre;
    item.querySelector(".recomendacion-precio").textContent = formatearPrecio(producto.precio);
    item.querySelector(".recomendacion-motivo").textContent = producto.razon;

    contenedor.appendChild(item);
}

function limpiarRecomendaciones(contenedor) {
    contenedor.replaceChildren();
}
