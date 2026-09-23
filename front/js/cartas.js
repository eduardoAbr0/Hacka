// Lógica de renderizado de las cartas de productos

const IMAGEN_POR_DEFECTO =
    "data:image/svg+xml;utf8," +
    encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 3"><rect width="4" height="3" fill="#e9ecef"/></svg>');

function formatearPrecio(precio) {
    return precio.toLocaleString("es-MX", { style: "currency", currency: "MXN" });
}

function crearCarta(producto) {
    const carta = document.createElement("article");
    carta.className = "carta";
    carta.dataset.id = producto.id;

    carta.innerHTML = `
        <img class="carta-imagen" alt="">
        <div class="carta-cuerpo">
            <h2 class="carta-nombre"></h2>
            <p class="carta-descripcion"></p>
            <div class="carta-pie">
                <span class="carta-precio"></span>
                <button class="carta-boton" type="button">Ver</button>
            </div>
        </div>
    `;

    const img = carta.querySelector(".carta-imagen");
    img.src = producto.imagen || IMAGEN_POR_DEFECTO;
    img.alt = producto.nombre;
    carta.querySelector(".carta-nombre").textContent = producto.nombre;
    carta.querySelector(".carta-descripcion").textContent = producto.descripcion;
    carta.querySelector(".carta-precio").textContent = formatearPrecio(producto.precio);

    return carta;
}

function renderizarCartas(productos, contenedor) {
    contenedor.replaceChildren(...productos.map(crearCarta));
}
