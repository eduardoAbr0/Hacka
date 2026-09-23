// Punto de entrada: conecta datos, cartas, recomendaciones y modal

// Productos cargados, separados porque un mismo producto puede venir con distinta razón
let PERSONALES = [];
let GENERALES = [];

const MENSAJE_SIN_API = "No pudimos cargar los productos. Revisa que la API (api_web.py) esté encendida.";

function abrirProductoPorId(lista, id) {
    const producto = lista.find((p) => p.id === id);
    if (producto) modal.abrir(producto);
}

// Panel lateral: recomendaciones personales del cliente
async function cargarPersonales(contenedor) {
    agregarRecomendacion(contenedor, "Buscando productos para ti…", "Un momento ⏳");
    try {
        // Solo las personales; las populares ya se muestran en las cartas
        PERSONALES = (await obtenerRecomendaciones(obtenerClienteId())).filter((p) => p.personalizado);
    } catch (err) {
        console.error("[Recomendaciones]", err);
        limpiarRecomendaciones(contenedor);
        agregarRecomendacion(contenedor, MENSAJE_SIN_API, "Sin conexión ⚠️");
        return;
    }

    limpiarRecomendaciones(contenedor);
    if (PERSONALES.length === 0) {
        agregarRecomendacion(contenedor,
            "Aún no conocemos tus gustos. Mientras tanto, mira lo más vendido de la tienda. Con tus compras te sugeriremos productos a tu medida.",
            "¡Bienvenido! 👋");
        return;
    }
    agregarRecomendacion(contenedor, "Elegimos estos productos pensando en ti. Tócalos para saber por qué.", "¡Hola! 👋");
    PERSONALES.forEach((p) => agregarProductoRecomendado(contenedor, p));
}

// Cartas: productos populares para todos
async function cargarGenerales(contenedor) {
    try {
        GENERALES = await obtenerPopulares();
    } catch (err) {
        console.error("[Populares]", err);
        const aviso = document.createElement("p");
        aviso.className = "aviso";
        aviso.textContent = MENSAJE_SIN_API;
        contenedor.replaceChildren(aviso);
        return;
    }
    renderizarCartas(GENERALES, contenedor);
}

document.addEventListener("DOMContentLoaded", () => {
    const contenedor = document.getElementById("contenedor-cartas");
    const recomendaciones = document.getElementById("recomendaciones");

    // Barra superior
    document.getElementById("nombre-negocio").textContent = NEGOCIO.nombre;
    document.getElementById("logo-negocio").src = NEGOCIO.logo;
    document.title = NEGOCIO.nombre;

    modal.iniciar();

    // "Ver" en una carta o clic en una sugerencia abren el modal con la razón
    contenedor.addEventListener("click", (e) => {
        const boton = e.target.closest(".carta-boton");
        if (boton) abrirProductoPorId(GENERALES, Number(boton.closest(".carta").dataset.id));
    });
    recomendaciones.addEventListener("click", (e) => {
        const item = e.target.closest(".recomendacion-producto");
        if (item) abrirProductoPorId(PERSONALES, Number(item.dataset.id));
    });

    cargarPersonales(recomendaciones);
    cargarGenerales(contenedor);
});
