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

function limpiarRecomendaciones(contenedor) {
    contenedor.replaceChildren();
}
