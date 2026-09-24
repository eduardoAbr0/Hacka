// Lógica de la página "Mi carrito"

const CLAVE_GUARDADO = "compras";

// Estado de compras y autenticación facial del cliente
let compras = cargarCompras();
let clienteActivo = null; // { id, codigo, nombre } o null
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

    const imgEl = li.querySelector(".compra-imagen");
    imgEl.src = p.imagen || p.imagen_url || IMAGEN_POR_DEFECTO;
    imgEl.onerror = () => { imgEl.src = IMAGEN_POR_DEFECTO; };
    imgEl.alt = p.nombre;

    li.querySelector(".compra-nombre").textContent = p.nombre;
    li.querySelector(".compra-detalle").textContent =
        `${compra.cantidad} × ${formatearPrecio(p.precio)}`;
    li.querySelector(".compra-subtotal").textContent = formatearPrecio(p.precio * compra.cantidad);

    // Botones para quitar / sumar unidades (solo si hay cliente activo)
    const control = document.createElement("div");
    control.className = "cantidad-control";
    control.innerHTML = `
        <button class="cantidad-btn" type="button" data-cambio="-1" aria-label="Quitar una unidad" ${!clienteActivo ? 'disabled' : ''}>−</button>
        <button class="cantidad-btn" type="button" data-cambio="1" aria-label="Agregar una unidad" ${!clienteActivo ? 'disabled' : ''}>+</button>
    `;
    control.querySelector('[data-cambio="-1"]').disabled = !clienteActivo || compra.cantidad <= 1;
    li.querySelector(".compra-subtotal").before(control);
    return li;
}

function renderizar() {
    const lista = document.getElementById("lista-compras");
    const validas = compras.filter((c) => buscarProducto(c.id));

    if (validas.length === 0) {
        lista.innerHTML = `<li class="lista-vacia">Tu carrito está vacío.<br>${clienteActivo ? 'Escanea un código de barras para empezar.' : 'Acércate a la cámara facial para empezar.'}</li>`;
    } else {
        lista.replaceChildren(...validas.map(crearItemCompra));
    }

    const { cantidad, total } = calcularTotales();
    document.getElementById("conteo-productos").textContent =
        `${validas.length} ${validas.length === 1 ? "artículo" : "artículos"}`;
    document.getElementById("resumen-cantidad").textContent = cantidad;
    document.getElementById("resumen-total").textContent = formatearPrecio(total);

    // Renderizar Banner de Estado Facial
    const banner = document.getElementById("banner-facial");
    const icono = document.getElementById("facial-icono");
    const titulo = document.getElementById("facial-titulo");
    const subtitulo = document.getElementById("facial-subtitulo");
    const avisoEscanear = document.getElementById("aviso-escanear");
    const resumenCliente = document.getElementById("resumen-cliente");
    const btnPagar = document.getElementById("btn-pagar");
    const btnEliminar = document.getElementById("btn-eliminar");

    if (clienteActivo) {
        if (banner) {
            banner.className = "banner-facial desbloqueado";
            icono.textContent = "👤";
            titulo.textContent = `Cliente Identificado: ${clienteActivo.nombre || clienteActivo.codigo}`;
            subtitulo.textContent = "Desbloqueado · Escanea productos usando la cámara del celular.";
        }
        if (avisoEscanear) avisoEscanear.style.display = "flex";
        if (resumenCliente) {
            resumenCliente.textContent = `${clienteActivo.nombre || clienteActivo.codigo} ✅`;
            resumenCliente.style.color = "#059669";
        }
        btnPagar.disabled = (validas.length === 0);
    } else {
        if (banner) {
            banner.className = "banner-facial bloqueado";
            icono.textContent = "🔒";
            titulo.textContent = "Identificación Facial Requerida";
            subtitulo.textContent = "Acércate a la cámara de la laptop para identificarte con tu rostro.";
        }
        if (avisoEscanear) avisoEscanear.style.display = "none";
        if (resumenCliente) {
            resumenCliente.textContent = "Sin identificar 🔒";
            resumenCliente.style.color = "#dc2626";
        }
        btnPagar.disabled = true;
    }

    btnEliminar.disabled = seleccionadas.size === 0 || !clienteActivo;
    document.getElementById("btn-cancelar").disabled = cantidad === 0;
}

/* ---------- Acciones ---------- */
function agregarProducto(id) {
    if (!clienteActivo) {
        if (typeof dialogo !== "undefined" && dialogo.mensaje) {
            dialogo.mensaje({
                icono: "🔒",
                titulo: "Identificación Facial Requerida",
                texto: "Debes estar identificado frente a la cámara de la laptop antes de agregar productos al carrito.",
                textoSi: "Entendido"
            });
        } else {
            alert("🔒 Debes estar identificado frente a la cámara de la laptop antes de agregar productos.");
        }
        return;
    }

    const existente = compras.find((c) => c.id === id);
    if (existente) existente.cantidad++;
    else compras.push({ id, cantidad: 1 });
    guardarCompras();
    renderizar();
}

function cambiarCantidad(id, cambio) {
    if (!clienteActivo) return;
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

/* ---------- Monitoreo de Estado Facial y Escáner ---------- */
let ultimoTimestampScan = null;

async function syncProductosBaseDatos() {
    if (typeof apiFotos === "undefined") return;
    const dbProds = await apiFotos.obtenerProductos();
    if (dbProds && dbProds.length > 0) {
        dbProds.forEach((dbP) => {
            const index = PRODUCTOS.findIndex((p) => p.id === dbP.id || p.codigo_barras === dbP.codigo_barras);
            if (index >= 0) {
                PRODUCTOS[index] = { ...PRODUCTOS[index], ...dbP };
            } else {
                PRODUCTOS.push(dbP);
            }
        });
        renderizar();
    }
}

async function monitorearEstadoYEscaneos() {
    // 1. Monitorear Estado de Identificación Facial
    try {
        const respCam = await fetch("/api/camara/estado");
        if (respCam.ok) {
            const estCam = await respCam.json();
            if (estCam && estCam.cliente_id) {
                if (!clienteActivo || clienteActivo.id !== estCam.cliente_id) {
                    clienteActivo = {
                        id: estCam.cliente_id,
                        codigo: estCam.codigo,
                        nombre: estCam.nombre || estCam.codigo
                    };
                    renderizar();
                }
            } else {
                if (clienteActivo !== null) {
                    clienteActivo = null;
                    renderizar();
                }
            }
        }
    } catch (e) { }

    // 2. Monitorear Escáner de Código de Barras
    if (typeof apiFotos === "undefined") return;
    try {
        const est = await apiFotos.estado();
        if (est && est.ultimo_escaneo && est.ultimo_escaneo.timestamp !== ultimoTimestampScan) {
            ultimoTimestampScan = est.ultimo_escaneo.timestamp;
            const esc = est.ultimo_escaneo;
            if (esc.producto) {
                let p = PRODUCTOS.find((x) => x.id === esc.producto.id || x.codigo_barras === esc.producto.codigo_barras);
                if (!p) {
                    p = esc.producto;
                    PRODUCTOS.push(p);
                }
                agregarProducto(p.id);
                const aviso = document.querySelector(".aviso-escanear");
                if (aviso && clienteActivo) {
                    aviso.innerHTML = `<span class="aviso-icono">✨</span> ¡Producto Agregado!: <strong>${p.nombre}</strong> (${formatearPrecio(p.precio)})`;
                    aviso.style.background = "#d1fae5";
                    aviso.style.color = "#065f46";
                    aviso.style.border = "1px solid #a7f3d0";
                    setTimeout(() => {
                        aviso.innerHTML = `<span class="aviso-icono">📷</span> Para agregar tus compras, escanea el código de barras con la cámara`;
                        aviso.style.background = "";
                        aviso.style.color = "";
                        aviso.style.border = "";
                    }, 4000);
                }
            } else if (esc.tipo === "no_encontrado" || esc.codigo_barras) {
                if (typeof dialogo !== "undefined" && dialogo.mensaje) {
                    dialogo.mensaje({
                        icono: "❌",
                        titulo: "Producto no encontrado",
                        texto: `El código de barras "${esc.codigo_barras}" fue analizado pero no existe en el inventario.`,
                        textoSi: "Entendido"
                    });
                }
            }
        }
    } catch (e) { }
}

/* ---------- Inicio ---------- */
document.addEventListener("DOMContentLoaded", () => {
    iniciarBarraSuperior();
    dialogo.iniciar();
    syncProductosBaseDatos();
    renderizar();

    // Monitorear estado facial y escáner cada 1.5 segundos
    setInterval(monitorearEstadoYEscaneos, 1500);

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

    // Pagar y registrar venta vinculada al cliente identificado
    document.getElementById("btn-pagar").addEventListener("click", () => {
        if (!clienteActivo) {
            alert("🔒 Debes estar identificado frente a la cámara facial para realizar la compra.");
            return;
        }

        const validas = compras.filter((c) => buscarProducto(c.id));
        if (validas.length === 0) return;

        const { total } = calcularTotales();
        const payloadVenta = {
            cliente_id: clienteActivo.id,
            items: validas.map((c) => ({ producto_id: c.id, cantidad: c.cantidad }))
        };

        dialogo.mensaje({
            icono: "💳",
            titulo: "¿Confirmar compra?",
            texto: `Cliente: ${clienteActivo.nombre || clienteActivo.codigo}\nTotal: ${formatearPrecio(total)}\nSe procesará el pago y registrará en la cuenta.`,
            textoSi: "Sí, Confirmar Pago",
            alConfirmar: async () => {
                try {
                    const resp = await fetch("/api/ventas", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payloadVenta)
                    });
                    const resData = await resp.json();

                    if (!resp.ok) throw new Error(resData.detail || "Error al procesar la venta");

                    vaciarCompras();
                    dialogo.mensaje({
                        icono: "✅",
                        titulo: "¡Pago Realizado con Éxito!",
                        texto: `Ticket #${resData.venta_id}\nCliente: ${clienteActivo.nombre || clienteActivo.codigo}\nTotal: ${formatearPrecio(total)}\n¡Gracias por tu compra!`
                    });
                } catch (err) {
                    dialogo.mensaje({
                        icono: "❌",
                        titulo: "Error en el Pago",
                        texto: err.message,
                        textoSi: "Entendido"
                    });
                }
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
