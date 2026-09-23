import sys
import os
from db_manager import DatabaseManager

def menu():
    db = DatabaseManager()
    # Precargar catálogo de ejemplo si está vacío
    db.precargar_productos_ejemplo()
    
    while True:
        status_db = "SQLite Cloud (NUBE)" if db.cloud_url else "SQLite Local (tienda.db)"
        print("\n" + "=" * 65)
        print("     SISTEMA DE TIENDA: PANEL DE ADMINISTRACION Y VENTAS")
        print(f"     BD Activa: {status_db}")
        print("=" * 65)
        print("  [1] Listar clientes y total de compras")
        print("  [2] Renombrar un cliente")
        print("  [3] Ver catalogo de productos y codigos de barra")
        print("  [4] Registrar nuevo producto (codigo de barras)")
        print("  [5] Registrar una venta a un cliente (caja)")
        print("  [6] Ver historial de ventas")
        print("  [7] Machine Learning: Ver datasets para recomendacion")
        print("  [8] Estadisticas generales")
        print("  [9] Configurar / Conectar a SQLite Cloud")
        print("  [0] Salir")
        
        opc = input("\nSeleccione una opcion (0-9): ").strip()
        
        if opc == "1":
            clientes = db.cargar_clientes()
            if not clientes:
                print("\n[!] No hay clientes registrados todavia.")
            else:
                print(f"\nTotal de clientes: {len(clientes)}")
                print("-" * 85)
                print(f"{'ID':<5} {'CODIGO':<10} {'NOMBRE':<26} {'COMPRAS':<10} {'GASTADO':<12} {'REGISTRO':<19}")
                print("-" * 85)
                for c in clientes:
                    gastado = f"${c['total_gastado']:.2f}"
                    print(f"{c['id']:<5} {c['codigo']:<10} {c['nombre']:<26} {c['total_compras']:<10} {gastado:<12} {c['fecha_registro']:<19}")
                print("-" * 85)

        elif opc == "2":
            codigo = input("Ingrese el codigo del cliente (ej. CLI-0001): ").strip().upper()
            clientes = db.cargar_clientes()
            encontrado = next((c for c in clientes if c["codigo"] == codigo), None)
            if not encontrado:
                print(f"[!] No se encontro ningun cliente con codigo {codigo}")
            else:
                print(f"Nombre actual: {encontrado['nombre']}")
                nuevo_nombre = input("Ingrese el nuevo nombre: ").strip()
                if nuevo_nombre:
                    db.actualizar_nombre_cliente(codigo, nuevo_nombre)
                    print(f"[OK] Cliente {codigo} actualizado a '{nuevo_nombre}'.")

        elif opc == "3":
            productos = db.listar_productos()
            print(f"\nCatalogo actual ({len(productos)} productos):")
            print("-" * 85)
            print(f"{'ID':<4} {'CODIGO BARRAS':<16} {'NOMBRE':<32} {'CATEGORIA':<12} {'PRECIO':<9} {'STOCK':<6}")
            print("-" * 85)
            for p in productos:
                precio_txt = f"${p['precio']:.2f}"
                print(f"{p['id']:<4} {p['codigo_barras']:<16} {p['nombre']:<32} {p['categoria']:<12} {precio_txt:<9} {p['stock']:<6}")
            print("-" * 85)

        elif opc == "4":
            print("\n--- REGISTRAR NUEVO PRODUCTO ---")
            codigo_barras = input("Codigo de barras (o escanear con lector): ").strip()
            if not codigo_barras:
                print("[!] El codigo de barras no puede estar vacio.")
                continue
            nombre = input("Nombre del producto: ").strip()
            categoria = input("Categoria (ej. Bebidas, Snacks, Abarrotes): ").strip() or "General"
            try:
                precio = float(input("Precio ($): ").strip())
                stock = int(input("Stock inicial (ej. 50): ").strip() or "50")
                origen = input("Origen (local / api) [local]: ").strip() or "local"
                db.crear_producto(codigo_barras, nombre, categoria, precio, stock, origen)
                print(f"[OK] Producto '{nombre}' guardado exitosamente.")
            except ValueError:
                print("[!] Error: Precio o stock con formato numerico incorrecto.")

        elif opc == "5":
            print("\n--- REGISTRAR VENTA ---")
            codigo_cliente = input("Codigo del cliente (ej. CLI-0001): ").strip().upper()
            clientes = db.cargar_clientes()
            cliente = next((c for c in clientes if c["codigo"] == codigo_cliente), None)
            if not cliente:
                print(f"[!] Cliente {codigo_cliente} no encontrado.")
                continue
            
            print(f"Cliente seleccionado: {cliente['nombre']} ({cliente['codigo']})")
            items = []
            
            while True:
                entrada = input("\nEscanee codigo de barras o ID de producto (o presione ENTER para cobrar): ").strip()
                if not entrada:
                    break
                
                prod = db.buscar_producto_por_codigo(entrada)
                if not prod and entrada.isdigit():
                    prods_all = db.listar_productos()
                    prod = next((p for p in prods_all if p["id"] == int(entrada)), None)
                
                if not prod:
                    print(f"[!] Producto no encontrado para '{entrada}'.")
                    continue
                
                try:
                    cant_str = input(f"Cantidad para '{prod['nombre']}' ($ {prod['precio']:.2f}) [1]: ").strip()
                    cant = int(cant_str) if cant_str else 1
                    items.append((prod["id"], cant))
                    print(f"   + Agregado: {prod['nombre']} x{cant} = ${prod['precio'] * cant:.2f}")
                except ValueError:
                    print("[!] Cantidad invalida.")

            if items:
                v_id, total = db.registrar_venta(cliente["id"], items)
                print(f"\n[EXITO] Venta #{v_id} registrada para {cliente['nombre']}. Total cobrado: ${total:.2f}")
            else:
                print("[!] No se agregaron productos a la venta.")

        elif opc == "6":
            ventas = db.obtener_historial_ventas(limite=20)
            if not ventas:
                print("\n[!] No hay ventas registradas aun.")
            else:
                print("\nUltimas 20 ventas:")
                print("-" * 80)
                print(f"{'VENTA #':<9} {'CLIENTE':<28} {'ITEMS':<8} {'TOTAL':<12} {'FECHA':<20}")
                print("-" * 80)
                for v in ventas:
                    cliente_txt = f"{v['cliente']} ({v['codigo']})"
                    total_txt = f"${v['total']:.2f}"
                    print(f"{v['venta_id']:<9} {cliente_txt:<28} {v['num_items']:<8} {total_txt:<12} {v['fecha']:<20}")
                print("-" * 80)

        elif opc == "7":
            print("\n" + "=" * 65)
            print("   DATASETS FORMATEADOS PARA MACHINE LEARNING")
            print("=" * 65)
            print("\n1. MATRIZ CLIENTE-PRODUCTO (Para Filtrado Colaborativo):")
            ds = db.obtener_dataset_cliente_producto()
            if not ds:
                print("   (Aun no hay ventas registradas para generar la matriz)")
            else:
                print(f"   Total de interacciones registradas: {len(ds)}")
                print(f"   {'CLIENTE':<20} {'PRODUCTO':<28} {'CATEGORIA':<12} {'VECES':<6} {'GASTO':<10}")
                print("   " + "-" * 75)
                for r in ds:
                    gasto_txt = f"${r['gasto_total']:.2f}"
                    print(f"   {r['cliente_nombre'][:18]:<20} {r['producto_nombre'][:26]:<28} {r['categoria']:<12} {r['frecuencia']:<6} {gasto_txt:<10}")

            print("\n2. CANASTAS DE COMPRA (Para Reglas de Asociacion Apriori / Market Basket):")
            canastas = db.obtener_canastas_compras()
            if not canastas:
                print("   (Aun no hay canastas de compra registradas)")
            else:
                print(f"   Total de tickets: {len(canastas)}")
                for i, c in enumerate(canastas, 1):
                    print(f"   Ticket #{i}: {', '.join(c)}")

        elif opc == "8":
            stats = db.contar_estadisticas()
            print("\nEstadisticas globales de la tienda:")
            print(f"- Clientes registrados: {stats['clientes']}")
            print(f"- Productos en catalogo: {stats['productos']}")
            print(f"- Ventas realizadas:     {stats['ventas']}")
            print(f"- Ingresos totales:      ${stats['ingresos']:.2f}")

        elif opc == "9":
            print("\n--- CONFIGURACION DE SQLITE CLOUD ---")
            print("Pega el Connection String de tu proyecto (https://sqlitecloud.io)")
            print("Ejemplo: sqlitecloud://xxxx.sqlite.cloud:8860/tienda.db?apikey=yyyy")
            print("(O escribe 'local' para volver a SQLite local)")
            nueva_url = input("\nURL: ").strip()
            if nueva_url.lower() == "local":
                if os.path.exists(db.config_path):
                    os.remove(db.config_path)
                db = DatabaseManager(cloud_url="")
                print("[OK] Cambiado a SQLite local (tienda.db).")
            elif nueva_url.startswith("sqlitecloud://"):
                try:
                    import sqlitecloud
                    conn_test = sqlitecloud.connect(nueva_url)
                    conn_test.close()
                    db.guardar_cloud_url(nueva_url)
                    db = DatabaseManager(cloud_url=nueva_url)
                    db.init_db()
                    db.precargar_productos_ejemplo()
                    print("[EXITO] Conectado exitosamente a SQLite Cloud.")
                except Exception as e:
                    print(f"[ERROR] No se pudo conectar: {e}")
            else:
                print("[!] URL invalida o vacia.")

        elif opc == "0":
            print("\nHasta luego.")
            break
        else:
            print("[!] Opcion no valida.")

if __name__ == "__main__":
    menu()
