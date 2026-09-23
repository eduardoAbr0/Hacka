// Lógica de la ventana emergente "¿Por qué te lo recomendamos?"

const modal = {
    el: null,

    iniciar() {
        this.el = document.getElementById("modal");
        this.el.addEventListener("click", (e) => {
            if (e.target.closest("[data-cerrar]")) this.cerrar();
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !this.el.hidden) this.cerrar();
        });
    },

    abrir(producto) {
        const img = document.getElementById("modal-imagen");
        img.src = producto.imagen || IMAGEN_POR_DEFECTO;
        img.alt = producto.nombre;
        document.getElementById("modal-titulo").textContent = producto.nombre;
        document.getElementById("modal-precio").textContent = formatearPrecio(producto.precio);
        document.getElementById("modal-razon").textContent =
            producto.razon || "Creemos que este producto puede interesarte.";

        this.el.hidden = false;
        document.body.classList.add("sin-scroll");
        this.el.querySelector(".modal-cerrar").focus();
    },

    cerrar() {
        this.el.hidden = true;
        document.body.classList.remove("sin-scroll");
    }
};
