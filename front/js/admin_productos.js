// Gestión de Registro e Inventario de Productos

let PRODUCTOS_TODOS = [];

function mostrarAlerta(mensaje, esError = false) {
    const alerta = document.getElementById("alerta");
    alerta.textContent = mensaje;
    alerta.className = `alerta-mensaje ${esError ? "alerta-error" : "alerta-exito"}`;
    alerta.style.display = "block";
    setTimeout(() => {
        alerta.style.display = "none";
    }, 4000);
}

async function cargarInventario() {
    const cuerpo = document.getElementById("tabla-cuerpo");
    const totalTxt = document.getElementById("total-productos-txt");

    try {
        const resp = await fetch("/api/productos");
        if (!resp.ok) throw new Error("Error al obtener productos");
        PRODUCTOS_TODOS = await resp.json();
        
        totalTxt.textContent = `Catálogo actual: ${PRODUCTOS_TODOS.length} productos registrados`;
        renderizarTabla(PRODUCTOS_TODOS);
    } catch (err) {
        console.error("[Inventario]", err);
        cuerpo.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#dc2626;">Error al cargar el inventario de productos.</td></tr>`;
    }
}

function renderizarTabla(lista) {
    const cuerpo = document.getElementById("tabla-cuerpo");
    if (lista.length === 0) {
        cuerpo.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--texto-suave);">No se encontraron productos en el inventario.</td></tr>`;
        return;
    }

    cuerpo.innerHTML = lista.map(p => `
        <tr>
            <td><strong>#${p.id}</strong></td>
            <td><code>${p.codigo_barras}</code></td>
            <td><strong>${p.nombre}</strong></td>
            <td>${p.categoria}</td>
            <td style="color:var(--acento); font-weight:700;">$${Number(p.precio).toFixed(2)}</td>
            <td>${p.stock} pzas</td>
            <td><span class="badge-origen ${p.origen === 'api' ? 'origen-api' : 'origen-local'}">${p.origen}</span></td>
        </tr>
    `).join("");
}

// Filtrar tabla dinámicamente
function filtrarTabla() {
    const query = document.getElementById("input-buscar").value.toLowerCase().strip();
    if (!query) {
        renderizarTabla(PRODUCTOS_TODOS);
        return;
    }
    const filtrados = PRODUCTOS_TODOS.filter(p => 
        p.nombre.toLowerCase().includes(query) || 
        p.codigo_barras.toLowerCase().includes(query) ||
        p.categoria.toLowerCase().includes(query)
    );
    renderizarTabla(filtrados);
}

// Autochequeo al ingresar código de barras
async function verificarCodigoBarras(codigo) {
    if (!codigo || codigo.length < 3) return;
    try {
        const resp = await fetch(`/api/productos/buscar/${encodeURIComponent(codigo)}`);
        const data = await resp.json();
        if (data.existe && data.producto) {
            const p = data.producto;
            document.getElementById("nombre").value = p.nombre;
            document.getElementById("categoria").value = p.categoria || "General";
            document.getElementById("precio").value = p.precio;
            document.getElementById("stock").value = p.stock;
            mostrarAlerta(`Código '${codigo}' ya existe. Los datos se actualizarán al guardar.`, false);
        }
    } catch (err) {
        // Ignorar
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("nombre-negocio").textContent = NEGOCIO.nombre;
    document.getElementById("logo-negocio").src = NEGOCIO.logo;

    const form = document.getElementById("form-producto");
    const inputCodigo = document.getElementById("codigo_barras");
    const inputBuscar = document.getElementById("input-buscar");

    cargarInventario();

    inputBuscar.addEventListener("input", filtrarTabla);

    inputCodigo.addEventListener("blur", () => {
        verificarCodigoBarras(inputCodigo.value.trim());
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
            codigo_barras: document.getElementById("codigo_barras").value.trim(),
            nombre: document.getElementById("nombre").value.trim(),
            categoria: document.getElementById("categoria").value,
            precio: parseFloat(document.getElementById("precio").value),
            stock: parseInt(document.getElementById("stock").value, 10),
            origen: "local"
        };

        try {
            const resp = await fetch("/api/productos", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const resData = await resp.json();
            if (!resp.ok) {
                throw new Error(resData.detail || "No se pudo guardar el producto");
            }

            mostrarAlerta(resData.mensaje || `Producto '${payload.nombre}' guardado con éxito.`);
            form.reset();
            inputCodigo.focus();
            cargarInventario();
        } catch (err) {
            mostrarAlerta(err.message, true);
        }
    });
});
