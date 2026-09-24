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
            let txt = `Última foto ${haceCuanto(estado.ultima_subida)}`;
            if (estado.ultimo_escaneo) {
                const esc = estado.ultimo_escaneo;
                if (esc.producto) {
                    txt += ` · 📦 ${esc.producto.nombre} (${esc.codigo_barras})`;
                } else if (esc.codigo_barras) {
                    txt += ` · ❌ Código ${esc.codigo_barras} (No encontrado en inventario)`;
                }
            }
            renderizarEstado(reciente, txt);
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

    // Cargar configuración de cámara IP
    apiFotos.configCamara().then((cfg) => {
        if (cfg && cfg.ip_cam_url) {
            const input = document.getElementById("input-ip-celular");
            if (input && !input.value) input.value = cfg.ip_cam_url;
        }
    }).catch(() => {});

    // Botón para guardar nueva IP de celular
    const btnGuardar = document.getElementById("btn-guardar-ip");
    if (btnGuardar) {
        btnGuardar.addEventListener("click", async () => {
            const input = document.getElementById("input-ip-celular");
            if (!input || !input.value.trim()) return;
            try {
                btnGuardar.textContent = "Guardando...";
                await apiFotos.guardarConfigCamara(input.value.trim());
                btnGuardar.textContent = "¡Guardado!";
                setTimeout(() => { btnGuardar.textContent = "Guardar IP"; }, 2000);
            } catch (err) {
                alert("Error al guardar IP de la cámara");
                btnGuardar.textContent = "Guardar IP";
            }
        });
    }

    // Botón para disparar foto con celular manualmente
    const btnTrigger = document.getElementById("btn-trigger");
    if (btnTrigger) {
        btnTrigger.addEventListener("click", async () => {
            try {
                btnTrigger.disabled = true;
                btnTrigger.textContent = "📸 Tomando foto HD...";
                const res = await apiFotos.trigger();
                if (res.ok) {
                    siguiendoUltima = true;
                    await actualizar();
                } else {
                    alert("Error: " + (res.error || "No se pudo tomar foto"));
                }
            } catch (err) {
                alert("Error al conectar con el servidor API");
            } finally {
                btnTrigger.disabled = false;
                btnTrigger.textContent = "📸 Tomar Foto Ahora (Celular)";
            }
        });
    }

    // Ver una foto de la galería
    document.getElementById("galeria-lista").addEventListener("click", (e) => {
        const item = e.target.closest(".galeria-item");
        if (!item) return;
        const foto = fotos.find((f) => f.nombre === item.dataset.nombre);
        siguiendoUltima = foto === fotos[0];
        mostrarFoto(foto);
    });
});
