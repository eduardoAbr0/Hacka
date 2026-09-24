// Punto de entrada de index.html: cartas, sugerencias, modal y monitoreo de la cámara.
// Para probar sin cámara: index.html?cliente=ID muestra directo a ese cliente.

const MENSAJE_SIN_API = "No pudimos cargar los productos. Revisa que la API (api_web.py) esté encendida.";

const TEXTO_ESTADO = {
    idle: "Esperando cliente",
    registrando: "Identificando rostro…",
    activo: "Cliente en pantalla",
    error: "Sin conexión con la API"
};

// Productos cargados, separados porque un mismo producto puede venir con distinta razón
let personales = [];
let generales = [];
let clienteActivo = null;

const el = {};

/* ---------- Productos ---------- */
function abrirProducto(lista, id) {
    const producto = lista.find((p) => p.id === id);
    if (producto) modal.abrir(producto);
}

async function cargarGenerales() {
    try {
        generales = await apiRecomendaciones.populares();
        renderizarCartas(generales, el.cartas);
    } catch (err) {
        console.error("[Populares]", err);
        const aviso = document.createElement("p");
        aviso.className = "aviso";
        aviso.textContent = MENSAJE_SIN_API;
        el.cartas.replaceChildren(aviso);
    }
}

async function cargarPersonales(clienteId) {
    limpiarRecomendaciones(el.sugerencias);
    agregarRecomendacion(el.sugerencias, "Buscando productos para ti…", "Un momento ⏳");

    let datos;
    try {
        datos = await apiRecomendaciones.personales(clienteId);
    } catch (err) {
        console.error("[Recomendaciones]", err);
        datos = null;
    }
    // Si mientras tanto llegó otro cliente, estos datos ya no sirven
    if (clienteId !== clienteActivo) return;

    limpiarRecomendaciones(el.sugerencias);
    if (datos === null) {
        agregarRecomendacion(el.sugerencias, MENSAJE_SIN_API, "Sin conexión ⚠️");
        return;
    }

    personales = datos;
    if (personales.length === 0) {
        mostrarSaludo("¡Bienvenido! 👋", "Tus sugerencias aparecerán con tus compras");
        agregarRecomendacion(el.sugerencias,
            "Aún no conocemos tus gustos. Mientras tanto, mira lo más vendido de la tienda.");
        return;
    }
    mostrarSaludo("¡Hola de nuevo! 👋", "Según tus compras anteriores");
    agregarRecomendacion(el.sugerencias, "Toca un producto para saber por qué te lo recomendamos.");
    personales.forEach((p) => agregarProductoRecomendado(el.sugerencias, p));
}

/* ---------- Cliente frente a la cámara ---------- */
function mostrarSaludo(titulo, subtitulo) {
    el.saludoTitulo.textContent = titulo;
    el.saludoSubtitulo.textContent = subtitulo;
}

function mostrarEstadoCamara(estado) {
    el.estadoCamara.classList.toggle("error", estado === "error");
    el.estadoCamaraTexto.textContent = TEXTO_ESTADO[estado] || TEXTO_ESTADO.idle;
}

function aplicarEstado(estado, clienteId) {
    mostrarEstadoCamara(estado);
    el.espera.hidden = estado !== "idle";

    if (estado === "idle") {
        // Se borran los datos del cliente anterior para que el siguiente no los vea
        if (clienteActivo !== null) limpiarRecomendaciones(el.sugerencias);
        clienteActivo = null;
        personales = [];
    } else if (estado === "registrando" && clienteActivo === null) {
        mostrarSaludo("¡Bienvenido! 👋", "Identificando tu perfil…");
        limpiarRecomendaciones(el.sugerencias);
        agregarRecomendacion(el.sugerencias, "Mira a la cámara un momento, por favor.", "Un momento ⏳");
    } else if (estado === "activo" && clienteId && clienteId !== clienteActivo) {
        clienteActivo = clienteId;
        cargarPersonales(clienteId);
    }
}

// Consulta la cámara, espera la respuesta y vuelve a consultar
async function monitorearCamara() {
    try {
        const data = await apiRecomendaciones.estadoCamara();
        aplicarEstado(data.estado || "idle", data.cliente_id);
    } catch (err) {
        mostrarEstadoCamara("error");
    }
    setTimeout(monitorearCamara, RECOMENDADOR.intervaloCamaraMs);
}

/* ---------- Inicio ---------- */
document.addEventListener("DOMContentLoaded", () => {
    el.cartas = document.getElementById("contenedor-cartas");
    el.sugerencias = document.getElementById("recomendaciones");
    el.espera = document.getElementById("pantalla-espera");
    el.estadoCamara = document.getElementById("estado-camara");
    el.estadoCamaraTexto = document.getElementById("estado-camara-texto");
    el.saludoTitulo = document.getElementById("saludo-titulo");
    el.saludoSubtitulo = document.getElementById("saludo-subtitulo");

    iniciarBarraSuperior();
    document.title = NEGOCIO.nombre;
    modal.iniciar();

    el.cartas.addEventListener("click", (e) => {
        const boton = e.target.closest(".carta-boton");
        if (boton) abrirProducto(generales, Number(boton.closest(".carta").dataset.id));
    });
    el.sugerencias.addEventListener("click", (e) => {
        const item = e.target.closest(".recomendacion-producto");
        if (item) abrirProducto(personales, Number(item.dataset.id));
    });

    cargarGenerales();

    const clientePrueba = Number(new URLSearchParams(location.search).get("cliente"));
    if (Number.isInteger(clientePrueba) && clientePrueba > 0) {
        el.espera.hidden = true;
        el.estadoCamaraTexto.textContent = `Modo prueba · cliente ${clientePrueba}`;
        clienteActivo = clientePrueba;
        cargarPersonales(clientePrueba);
    } else {
        monitorearCamara();
    }
});
