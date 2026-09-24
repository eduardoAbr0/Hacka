// Lógica de la página "Cámara"
// El ESP32 toma las fotos solo (sensor ultrasónico); la página revisa cada pocos segundos si llegó una nueva.

const INTERVALO_ACTUALIZAR_MS = 2000;
const RECIENTE_MS = 60 * 1000;   // el indicador se pone verde si hubo foto en el último minuto

let fotos = [];
let fotoMostrada = null;       // nombre de la foto en el visor
let siguiendoUltima = true;    // si el visor cambia solo cuando llega una foto nueva

/* ---------- Render ---------- */
function formatearFecha(iso) {
    return new Date(iso).toLocaleString("es-MX", { dateStyle: "medium", timeStyle: "short" });
}

function haceCuanto(iso) {
    const seg = Math.max(0, Math.round((Date.now() - new Date(iso)) / 1000));
    if (seg < 60) return `hace ${seg} s`;
    if (seg < 3600) return `hace ${Math.round(seg / 60)} min`;
    return formatearFecha(iso);
}

function mostrarFoto(foto) {
    const img = document.getElementById("foto-grande");
    const vacio = document.getElementById("visor-vacio");

    if (!foto) {
        img.hidden = true;
        vacio.hidden = false;
        document.getElementById("foto-info").textContent = "";
        fotoMostrada = null;
        return;
    }

    img.src = apiFotos.urlFoto(foto);
    img.hidden = false;
    vacio.hidden = true;
    document.getElementById("foto-info").textContent =
        `${formatearFecha(foto.fecha)} · ${(foto.tamano / 1024).toFixed(0)} KB`;
    fotoMostrada = foto.nombre;
    marcarActiva();
}

function marcarActiva() {
    document.querySelectorAll(".galeria-item").forEach((el) => {
        el.classList.toggle("activa", el.dataset.nombre === fotoMostrada);
    });
}

function renderizarGaleria() {
    const lista = document.getElementById("galeria-lista");
    document.getElementById("galeria-conteo").textContent = fotos.length ? `(${fotos.length})` : "";

    if (fotos.length === 0) {
        lista.innerHTML = `<li class="galeria-vacia">Las fotos del ESP32 aparecerán aquí.</li>`;
        return;
    }

    lista.replaceChildren(...fotos.map((foto) => {
        const li = document.createElement("li");
        li.innerHTML = `
            <button class="galeria-item" type="button">
                <img class="galeria-miniatura" loading="lazy" alt="">
                <span class="galeria-fecha"></span>
            </button>
        `;
        li.querySelector("button").dataset.nombre = foto.nombre;
        li.querySelector("img").src = apiFotos.urlFoto(foto);
        li.querySelector(".galeria-fecha").textContent = formatearFecha(foto.fecha);
        return li;
    }));
    marcarActiva();
}

function renderizarEstado(activo, texto) {
    const el = document.getElementById("estado-esp32");
    el.classList.toggle("conectado", activo);
    el.classList.toggle("desconectado", !activo);
    document.getElementById("estado-texto").textContent = texto;
}

/* ---------- Actualización periódica ---------- */
async function actualizar() {
    try {
        const [estado, lista] = await Promise.all([apiFotos.estado(), apiFotos.listar()]);

        const cambio = lista.length !== fotos.length || lista[0]?.nombre !== fotos[0]?.nombre;
        fotos = lista;
        if (cambio) renderizarGaleria();
        if (siguiendoUltima && fotos[0]?.nombre !== fotoMostrada) mostrarFoto(fotos[0]);

        if (estado.ultima_subida) {
            const reciente = Date.now() - new Date(estado.ultima_subida) < RECIENTE_MS;
            renderizarEstado(reciente, `Última foto ${haceCuanto(estado.ultima_subida)} (${estado.ip_esp32})`);
        } else {
            renderizarEstado(false, "Esperando la primera foto del ESP32");
        }
    } catch (e) {
        renderizarEstado(false, "No se encontró la API (¿está corriendo API_foto.py?)");
    }
}

/* ---------- Inicio ---------- */
document.addEventListener("DOMContentLoaded", () => {
    iniciarBarraSuperior();
    actualizar();
    setInterval(actualizar, INTERVALO_ACTUALIZAR_MS);

    // Ver una foto de la galería
    document.getElementById("galeria-lista").addEventListener("click", (e) => {
        const item = e.target.closest(".galeria-item");
        if (!item) return;
        const foto = fotos.find((f) => f.nombre === item.dataset.nombre);
        siguiendoUltima = foto === fotos[0];
        mostrarFoto(foto);
    });
});
