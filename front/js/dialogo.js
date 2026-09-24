// Diálogos reutilizables (ventanas emergentes) para la página de ventas

const dialogo = {
    abrir(el) {
        el.hidden = false;
        document.body.classList.add("sin-scroll");
    },

    cerrar(el) {
        el.hidden = true;
        if (!document.querySelector(".dialogo:not([hidden])")) {
            document.body.classList.remove("sin-scroll");
        }
    },

    // Cierra con la X, el fondo, botones [data-cerrar] o la tecla Esc
    iniciar() {
        document.querySelectorAll(".dialogo").forEach((el) => {
            el.addEventListener("click", (e) => {
                if (e.target.closest("[data-cerrar]")) this.cerrar(el);
            });
        });
        document.addEventListener("keydown", (e) => {
            if (e.key !== "Escape") return;
            document.querySelectorAll(".dialogo:not([hidden])").forEach((el) => this.cerrar(el));
        });
    },

    // Muestra un mensaje. "icono" es un nombre de Font Awesome sólido (ej. "lock", "trash").
    // Si se pasa "alConfirmar", aparecen los botones Sí / No.
    mensaje({ icono = "", titulo, texto = "", textoSi = "Aceptar", alConfirmar = null }) {
        const el = document.getElementById("dialogo-mensaje");
        const si = document.getElementById("mensaje-si");
        const no = document.getElementById("mensaje-no");

        const iconoEl = document.getElementById("mensaje-icono");
        iconoEl.replaceChildren();
        if (icono) {
            const i = document.createElement("i");
            i.className = `fa-solid fa-${icono}`;
            iconoEl.appendChild(i);
        }
        document.getElementById("mensaje-titulo").textContent = titulo;
        document.getElementById("mensaje-texto").textContent = texto;
        si.textContent = textoSi;
        no.hidden = !alConfirmar;

        si.onclick = () => {
            this.cerrar(el);
            if (alConfirmar) alConfirmar();
        };

        this.abrir(el);
        si.focus();
    }
};
