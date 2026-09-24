// Catálogo de productos de la tienda con imágenes de alta calidad
let PRODUCTOS = [
    { id: 1, codigo_barras: "7501055310884", nombre: "Coca-Cola Original 600ml", categoria: "Bebidas", precio: 18.50, imagen: "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop", razon: "Es de los productos más populares e icónicos." },
    { id: 2, codigo_barras: "7501000111207", nombre: "Papas Sabritas Sal 45g", categoria: "Snacks", precio: 22.00, imagen: "https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=500&auto=format&fit=crop", razon: "Excelente botana crujiente para acompañar cualquier bebida." },
    { id: 3, codigo_barras: "7501030467145", nombre: "Agua Ciel Purificada 1L", categoria: "Bebidas", precio: 14.00, imagen: "https://images.unsplash.com/photo-1548839140-29a749e1bc4e?w=500&auto=format&fit=crop", razon: "Hidratación indispensable y refrescante." },
    { id: 4, codigo_barras: "7501000153108", nombre: "Galletas Emperador Chocolate 101g", categoria: "Snacks", precio: 19.50, imagen: "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=500&auto=format&fit=crop", razon: "Rellenas de delicioso chocolate crujiente." },
    { id: 5, codigo_barras: "7501020512345", nombre: "Leche Lala Entera 1L", categoria: "Lácteos", precio: 26.50, imagen: "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=500&auto=format&fit=crop", razon: "Leche 100% pura y fresca de la mejor calidad." },
    { id: 6, codigo_barras: "7501032300129", nombre: "Café Soluble Nescafé Clásico 120g", categoria: "Abarrotes", precio: 68.00, imagen: "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=500&auto=format&fit=crop", razon: "El aroma y sabor clásico para iniciar las mañanas." }
];

// Carga asíncrona para sincronizar con la base de datos de la API
async function cargarProductosDesdeAPI() {
    try {
        const resp = await fetch("/api/productos");
        if (resp.ok) {
            const apiProds = await resp.json();
            if (Array.isArray(apiProds) && apiProds.length > 0) {
                PRODUCTOS = apiProds.map(p => ({
                    id: p.id,
                    codigo_barras: p.codigo_barras,
                    nombre: p.nombre,
                    categoria: p.categoria,
                    precio: p.precio,
                    stock: p.stock,
                    imagen: p.imagen_url || p.imagen || "https://images.unsplash.com/photo-1542838132-92c53300491e?w=500&auto=format&fit=crop",
                    razon: `Producto disponible en la categoría ${p.categoria}.`
                }));
            }
        }
    } catch (e) {
        // Usa el catálogo estático predeterminado
    }
}

cargarProductosDesdeAPI();
