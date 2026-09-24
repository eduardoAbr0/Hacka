// Punto de entrada: conecta datos, cartas, recomendaciones y modal

document.addEventListener("DOMContentLoaded", () => {
    const contenedor = document.getElementById("contenedor-cartas");
    const recomendaciones = document.getElementById("recomendaciones");

    // Barra superior
    iniciarBarraSuperior();
    document.title = NEGOCIO.nombre;

    renderizarCartas(PRODUCTOS, contenedor);
    modal.iniciar();

    agregarRecomendacion(recomendaciones,
        "Dale clic en «Ver» en cualquier producto para saber por qué te lo recomendamos.",
        "¡Hola! 👋");

    // Al pulsar "Ver" se abre la ventana con la razón de la recomendación
    contenedor.addEventListener("click", (e) => {
        const boton = e.target.closest(".carta-boton");
        if (!boton) return;
        const id = Number(boton.closest(".carta").dataset.id);
        const producto = PRODUCTOS.find((p) => p.id === id);
        if (producto) modal.abrir(producto);
    });
});
