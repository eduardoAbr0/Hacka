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
        cuerpo.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--texto-suave);">No se encontraron productos en el inventario.</td></tr>`;
        return;
    }

    cuerpo.innerHTML = lista.map(p => {
        const imgUrl = p.imagen_url || "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 100 100"><rect width="100" height="100" fill="#f1f5f9"/><text x="50" y="55" font-size="30" text-anchor="middle" fill="#94a3b8">📦</text></svg>');
        return `
            <tr>
                <td><img src="${imgUrl}" alt="${p.nombre}" style="width: 42px; height: 42px; object-fit: cover; border-radius: 6px; border: 1px solid var(--borde);" onerror="this.src='${imgUrl}';"></td>
                <td><strong>#${p.id}</strong></td>
                <td><code>${p.codigo_barras}</code></td>
                <td><strong>${p.nombre}</strong></td>
                <td>${p.categoria}</td>
                <td style="color:var(--acento); font-weight:700;">$${Number(p.precio).toFixed(2)}</td>
                <td>${p.stock} pzas</td>
                <td><span class="badge-origen ${p.origen === 'api' ? 'origen-api' : 'origen-local'}">${p.origen}</span></td>
            </tr>
        `;
    }).join("");
}

// Filtrar tabla dinámicamente
function filtrarTabla() {
    const query = document.getElementById("input-buscar").value.toLowerCase().trim();
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
            if (document.getElementById("imagen_url")) {
                document.getElementById("imagen_url").value = p.imagen_url || "";
            }
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

        const imgInput = document.getElementById("imagen_url");
        const payload = {
            codigo_barras: document.getElementById("codigo_barras").value.trim(),
            nombre: document.getElementById("nombre").value.trim(),
            categoria: document.getElementById("categoria").value,
            precio: parseFloat(document.getElementById("precio").value),
            stock: parseInt(document.getElementById("stock").value, 10),
            origen: "local",
            imagen_url: imgInput ? imgInput.value.trim() : null
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
