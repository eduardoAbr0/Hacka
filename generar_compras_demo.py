import random
import numpy as np
from db_manager import DatabaseManager

def generar_datos_prueba():
    db = DatabaseManager()
    db.init_db()
    db.precargar_productos_ejemplo()

    print("=" * 65)
    print("      GENERADOR DE COMPRAS DE PRUEBA PARA MACHINE LEARNING")
    print("=" * 65)

    productos = db.listar_productos()
    if not productos:
        print("[!] No hay productos en el catálogo.")
        return

    # Buscar o crear clientes de prueba para simular patrones
    fake_enc = np.zeros(128, dtype=np.float64)
    
    clientes_demo = [
        ("CLI-0001", "Juan Perez (Snacks & Refrescos)"),
        ("CLI-0002", "Maria Gomez (Desayunos & Lacteos)"),
        ("CLI-0003", "Carlos Lopez (Snacks & Bebidas)"),
        ("CLI-0004", "Ana Martinez (Desayunos & Cafe)"),
        ("CLI-0005", "Pedro Ramirez (Variado)"),
    ]

    client_ids = []
    for cod, nom in clientes_demo:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM clientes WHERE codigo = ?", (cod,))
            row = cursor.fetchone()
            if row:
                client_ids.append((row[0], cod, nom))
            else:
                cid = db.registrar_cliente(cod, nom, fake_enc, "")
                client_ids.append((cid, cod, nom))

    # Mapear productos por categoría
    prod_dict = {p["nombre"]: p["id"] for p in productos}
    
    # Patrones de compra para entrenar el modelo de recomendaciones
    # Patrón 1: Refrescos + Snacks (Coca-Cola, Sabritas, Emperador)
    grupo_snack = [prod_dict.get("Coca-Cola Original 600ml"), 
                   prod_dict.get("Papas Sabritas Sal 45g"), 
                   prod_dict.get("Galletas Emperador Chocolate 101g")]
    
    # Patrón 2: Desayunos / Café (Leche Lala, Nescafé, Agua Ciel)
    grupo_desayuno = [prod_dict.get("Leche Lala Entera 1L"), 
                      prod_dict.get("Cafe Soluble Nescafe Clasico 120g"), 
                      prod_dict.get("Agua Ciel Purificada 1L")]

    # Generar 20 tickets de venta sintéticos
    total_ventas = 0
    for cid, cod, nom in client_ids:
        # Asignar preferencia según el cliente
        if "Snacks" in nom:
            base = grupo_snack
        elif "Desayunos" in nom:
            base = grupo_desayuno
        else:
            base = list(prod_dict.values())

        for _ in range(4): # 4 tickets por cliente
            p_seleccionados = random.sample([p for p in base if p is not None], k=random.randint(1, len(base)))
            items = [(p_id, random.randint(1, 2)) for p_id in p_seleccionados]
            v_id, total = db.registrar_venta(cid, items)
            total_ventas += 1

    stats = db.contar_estadisticas()
    print(f"[EXITO] {total_ventas} transacciones sintéticas generadas.")
    print(f"- Total de Ventas en la base: {stats['ventas']}")
    print(f"- Ingresos simulados: ${stats['ingresos']:.2f}")

if __name__ == "__main__":
    generar_datos_prueba()
