// Punto de entrada: conecta datos, escáner de cámara, cartas, recomendaciones y modal

let PERSONALES = [];
let GENERALES = [];
let CLIENTE_ACTIVO_ID = null;
let ESTADO_ACTUAL = "idle";

const MENSAJE_SIN_API = "No pudimos cargar los productos. Revisa que la API (api_web.py) esté encendida.";

function abrirProductoPorId(lista, id) {
    const producto = lista.find((p) => p.id === id);
    if (producto) modal.abrir(producto);
}

// Panel lateral: recomendaciones personales del cliente activo
async function cargarPersonales(contenedor, clienteId) {
    if (!clienteId) return;
    agregarRecomendacion(contenedor, "Buscando tus productos preferidos…", "Un momento ⏳");
    try {
        const data = await obtenerRecomendaciones(clienteId);
        PERSONALES = data;
    } catch (err) {
        console.error("[Recomendaciones]", err);
        limpiarRecomendaciones(contenedor);
        agregarRecomendacion(contenedor, MENSAJE_SIN_API, "Sin conexión ⚠️");
        return;
    }

    limpiarRecomendaciones(contenedor);
    if (PERSONALES.length === 0) {
        agregarRecomendacion(
            contenedor,
            "Aún no tenemos suficientes compras registradas para personalizar. Te sugerimos mirar los más vendidos.",
            "¡Bienvenido! 👋"
        );
        return;
    }

    agregarRecomendacion(contenedor, "Elegimos estos productos pensando en ti. Tócalos para saber por qué.", "¡Hola de nuevo! 👋");
    PERSONALES.forEach((p) => agregarProductoRecomendado(contenedor, p));
}

// Cartas: productos más vendidos para todos
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

// Monitoreo en tiempo real de la cámara para cambiar entre Espera y Activo
function iniciarMonitoreoCamara(recomendacionesElem, pantallaEsperaElem, textoStatusElem) {
    setInterval(async () => {
        try {
            const resp = await fetch("/api/camara/estado");
            if (!resp.ok) return;
            const data = await resp.json();

            const nuevoEstado = data.estado || "idle";
            const nuevoClienteId = data.cliente_id;

            if (textoStatusElem) {
                if (nuevoEstado === "idle") textoStatusElem.textContent = "Escáner en espera de cliente";
                else if (nuevoEstado === "registrando") textoStatusElem.textContent = "Identificando rostro...";
                else if (nuevoEstado === "activo") textoStatusElem.textContent = "Cliente en pantalla";
            }

            if (nuevoEstado === "idle") {
                if (ESTADO_ACTUAL !== "idle") {
                    ESTADO_ACTUAL = "idle";
                    CLIENTE_ACTIVO_ID = null;
                    pantallaEsperaElem.hidden = false;
                }
            } else if (nuevoEstado === "registrando") {
                if (pantallaEsperaElem.hidden === false) {
                    pantallaEsperaElem.hidden = true;
                }
                if (ESTADO_ACTUAL !== "registrando") {
                    ESTADO_ACTUAL = "registrando";
                    document.getElementById("titulo-saludo").textContent = "¡Bienvenido! 👋";
                    document.getElementById("subtitulo-saludo").textContent = "Identificando tu perfil por primera vez...";
                }
            } else if (nuevoEstado === "activo" && nuevoClienteId) {
                if (pantallaEsperaElem.hidden === false) {
                    pantallaEsperaElem.hidden = true;
                }
                if (CLIENTE_ACTIVO_ID !== nuevoClienteId) {
                    CLIENTE_ACTIVO_ID = nuevoClienteId;
                    ESTADO_ACTUAL = "activo";
                    document.getElementById("titulo-saludo").textContent = "¡Hola de nuevo! 👋";
                    document.getElementById("subtitulo-saludo").textContent = "Sugerencias seleccionadas para ti";
                    cargarPersonales(recomendacionesElem, nuevoClienteId);
                }
            }
        } catch (err) {
            // Ignorar errores de red temporales
        }
    }, 500);
}

document.addEventListener("DOMContentLoaded", () => {
    const contenedor = document.getElementById("contenedor-cartas");
    const recomendaciones = document.getElementById("recomendaciones");
    const pantallaEspera = document.getElementById("pantalla-espera");
    const textoStatus = document.getElementById("texto-camara-status");

    // Barra superior
    document.getElementById("nombre-negocio").textContent = NEGOCIO.nombre;
    document.getElementById("logo-negocio").src = NEGOCIO.logo;
    document.title = NEGOCIO.nombre;

    modal.iniciar();

    // Eventos de clic
    contenedor.addEventListener("click", (e) => {
        const boton = e.target.closest(".carta-boton");
        if (boton) abrirProductoPorId(GENERALES, Number(boton.closest(".carta").dataset.id));
    });
    recomendaciones.addEventListener("click", (e) => {
        const item = e.target.closest(".recomendacion-producto");
        if (item) abrirProductoPorId(PERSONALES, Number(item.dataset.id));
    });

    cargarGenerales(contenedor);
    iniciarMonitoreoCamara(recomendaciones, pantallaEspera, textoStatus);
});
