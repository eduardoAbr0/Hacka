// Lógica de renderizado de las cartas de productos

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
                <button class="carta-boton" type="button">Ver <i class="fa-solid fa-arrow-right"></i></button>
            </div>
        </div>
    `;

    const img = carta.querySelector(".carta-imagen");
    img.src = producto.imagen || producto.imagen_url || IMAGEN_POR_DEFECTO;
    img.onerror = () => { img.src = IMAGEN_POR_DEFECTO; };
    img.alt = producto.nombre;
    carta.querySelector(".carta-nombre").textContent = producto.nombre;
    carta.querySelector(".carta-descripcion").textContent = producto.descripcion;
    carta.querySelector(".carta-precio").textContent = formatearPrecio(producto.precio);

    return carta;
}

function renderizarCartas(productos, contenedor) {
    contenedor.replaceChildren(...productos.map(crearCarta));
}
