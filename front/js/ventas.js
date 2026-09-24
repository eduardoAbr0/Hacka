// Lógica de la página "Mi carrito"

const CLAVE_GUARDADO = "compras";

// Cada compra: { id del producto, cantidad }
let compras = cargarCompras();
const seleccionadas = new Set();

/* ---------- Guardado local (se conserva al recargar) ---------- */
function cargarCompras() {
    try {
        const guardadas = JSON.parse(localStorage.getItem(CLAVE_GUARDADO));
        if (Array.isArray(guardadas)) return guardadas;
    } catch (e) { /* sin almacenamiento disponible */ }

    // Compras de ejemplo la primera vez
    return [{ id: 1, cantidad: 2 }, { id: 3, cantidad: 1 }, { id: 4, cantidad: 1 }];
}

function guardarCompras() {
    try { localStorage.setItem(CLAVE_GUARDADO, JSON.stringify(compras)); } catch (e) { }
}

/* ---------- Cálculos ---------- */
function buscarProducto(id) {
    return PRODUCTOS.find((p) => p.id === id);
}

function calcularTotales() {
    return compras.reduce((acc, c) => {
        const p = buscarProducto(c.id);
        if (p) {
            acc.cantidad += c.cantidad;
            acc.total += p.precio * c.cantidad;
        }
        return acc;
    }, { cantidad: 0, total: 0 });
}

/* ---------- Render ---------- */
function crearItemCompra(compra) {
    const p = buscarProducto(compra.id);
    const li = document.createElement("li");
    li.className = "compra";
    li.dataset.id = compra.id;
    li.tabIndex = 0;
    li.classList.toggle("seleccionada", seleccionadas.has(compra.id));

    li.innerHTML = `
        <img class="compra-imagen" alt="">
        <div class="compra-info">
            <span class="compra-nombre"></span>
            <span class="compra-detalle"></span>
        </div>
        <span class="compra-subtotal"></span>
    `;

    li.querySelector(".compra-imagen").src = p.imagen || IMAGEN_POR_DEFECTO;
    li.querySelector(".compra-nombre").textContent = p.nombre;
    li.querySelector(".compra-detalle").textContent =
        `${compra.cantidad} × ${formatearPrecio(p.precio)}`;
    li.querySelector(".compra-subtotal").textContent = formatearPrecio(p.precio * compra.cantidad);

    // Botones para quitar / sumar unidades
    const control = document.createElement("div");
    control.className = "cantidad-control";
    control.innerHTML = `
        <button class="cantidad-btn" type="button" data-cambio="-1" aria-label="Quitar una unidad">−</button>
        <button class="cantidad-btn" type="button" data-cambio="1" aria-label="Agregar una unidad">+</button>
    `;
    control.querySelector('[data-cambio="-1"]').disabled = compra.cantidad <= 1;
    li.querySelector(".compra-subtotal").before(control);
    return li;
}

function renderizar() {
    const lista = document.getElementById("lista-compras");
    const validas = compras.filter((c) => buscarProducto(c.id));

    if (validas.length === 0) {
        lista.innerHTML = `<li class="lista-vacia">Tu carrito está vacío.<br>Escanea un código de barras para empezar.</li>`;
    } else {
        lista.replaceChildren(...validas.map(crearItemCompra));
    }

    const { cantidad, total } = calcularTotales();
    document.getElementById("conteo-productos").textContent =
        `${validas.length} ${validas.length === 1 ? "artículo" : "artículos"}`;
    document.getElementById("resumen-cantidad").textContent = cantidad;
    document.getElementById("resumen-total").textContent = formatearPrecio(total);

    document.getElementById("btn-eliminar").disabled = seleccionadas.size === 0;
    document.getElementById("btn-pagar").disabled = cantidad === 0;
    document.getElementById("btn-cancelar").disabled = cantidad === 0;
}

/* ---------- Acciones ---------- */
// Pensada para llamarse al escanear un código de barras
function agregarProducto(id) {
    const existente = compras.find((c) => c.id === id);
    if (existente) existente.cantidad++;
    else compras.push({ id, cantidad: 1 });
    guardarCompras();
    renderizar();
}

function cambiarCantidad(id, cambio) {
    const compra = compras.find((c) => c.id === id);
    if (!compra) return;
    compra.cantidad = Math.max(1, compra.cantidad + cambio);
    guardarCompras();
    renderizar();
}

function eliminarSeleccionadas() {
    compras = compras.filter((c) => !seleccionadas.has(c.id));
    seleccionadas.clear();
    guardarCompras();
    renderizar();
}

function vaciarCompras() {
    compras = [];
    seleccionadas.clear();
    guardarCompras();
    renderizar();
}

function alternarSeleccion(id) {
    if (seleccionadas.has(id)) seleccionadas.delete(id);
    else seleccionadas.add(id);
    renderizar();
}

/* ---------- Inicio ---------- */
document.addEventListener("DOMContentLoaded", () => {
    iniciarBarraSuperior();
    dialogo.iniciar();
    renderizar();

    const lista = document.getElementById("lista-compras");

    // Seleccionar compras (clic o Enter/Espacio)
    lista.addEventListener("click", (e) => {
        const item = e.target.closest(".compra");
        if (!item) return;
        const boton = e.target.closest(".cantidad-btn");
        if (boton) cambiarCantidad(Number(item.dataset.id), Number(boton.dataset.cambio));
        else alternarSeleccion(Number(item.dataset.id));
    });
    lista.addEventListener("keydown", (e) => {
        if (e.target.closest(".cantidad-btn")) return;
        const item = e.target.closest(".compra");
        if (item && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            alternarSeleccion(Number(item.dataset.id));
        }
    });

    // Eliminar seleccionadas
    document.getElementById("btn-eliminar").addEventListener("click", () => {
        const n = seleccionadas.size;
        dialogo.mensaje({
            icono: "🗑️",
            titulo: `¿Eliminar ${n} ${n === 1 ? "producto" : "productos"}?`,
            texto: "Se quitarán de tu carrito.",
            textoSi: "Sí, eliminar",
            alConfirmar: eliminarSeleccionadas
        });
    });

    // Pagar
    document.getElementById("btn-pagar").addEventListener("click", () => {
        const { total } = calcularTotales();
        dialogo.mensaje({
            icono: "💳",
            titulo: "¿Confirmar pago?",
            texto: `Se cobrará un total de ${formatearPrecio(total)}.`,
            textoSi: "Pagar",
            alConfirmar: () => {
                vaciarCompras();
                dialogo.mensaje({
                    icono: "✅",
                    titulo: "¡Pago realizado!",
                    texto: `Pagaste ${formatearPrecio(total)}. ¡Gracias por tu compra!`
                });
            }
        });
    });

    // Cancelar
    document.getElementById("btn-cancelar").addEventListener("click", () => {
        dialogo.mensaje({
            icono: "⚠️",
            titulo: "¿Cancelar la compra?",
            texto: "Se vaciará todo tu carrito.",
            textoSi: "Sí, cancelar",
            alConfirmar: vaciarCompras
        });
    });
});
