import os
import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from db_manager import DatabaseManager

MODEL_FILE = "modelo_recomendacion.joblib"

class RecomendadorProductos:
    def __init__(self, db=None, model_path=None):
        self.db = db or DatabaseManager()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = model_path or os.path.join(base_dir, MODEL_FILE)
        
        self.user_ids = []
        self.product_ids = []
        self.user_item_matrix = None
        self.user_similarity = None
        self.productos_map = {}
        self.popular_products = []

        # Intentar cargar modelo si ya fue entrenado anteriormente
        self.cargar_modelo()

    def entrenar_modelo(self):
        """
        Extrae datos de ventas, construye la matriz Usuario-Ítem con Scikit-Learn,
        calcula la Similitud de Cosenos y guarda el modelo serializado (.joblib).
        """
        dataset = self.db.obtener_dataset_cliente_producto()
        productos = self.db.listar_productos()

        if not dataset or not productos:
            print("[Recomendador ML] Sin datos suficientes para entrenar. Se usará catálogo por defecto.")
            self._construir_fallback_popular(productos)
            return False

        # Mapeo rápido de información de productos
        self.productos_map = {p["id"]: p for p in productos}
        
        # Identificar IDs únicos de usuarios y productos
        unique_users = sorted(list(set(row["cliente_id"] for row in dataset)))
        unique_products = sorted(list(set(p["id"] for p in productos)))

        user_to_idx = {u_id: idx for idx, u_id in enumerate(unique_users)}
        prod_to_idx = {p_id: idx for idx, p_id in enumerate(unique_products)}

        # Construir matriz de frecuencia Usuario-Ítem
        matrix = np.zeros((len(unique_users), len(unique_products)), dtype=np.float64)

        for row in dataset:
            u_idx = user_to_idx.get(row["cliente_id"])
            p_idx = prod_to_idx.get(row["producto_id"])
            if u_idx is not None and p_idx is not None:
                matrix[u_idx, p_idx] = float(row["frecuencia"])

        # 1. Calcular Similitud de Cosenos entre Usuarios con Scikit-Learn
        # cosine_similarity retorna una matriz [N_users x N_users] con valores entre 0 y 1
        user_sim = cosine_similarity(matrix)

        # 2. Calcular los productos más populares para clientes nuevos (Cold Start)
        popular_counts = np.sum(matrix, axis=0)
        top_prod_indices = np.argsort(popular_counts)[::-1]
        self.popular_products = [unique_products[idx] for idx in top_prod_indices if popular_counts[idx] > 0]

        # Guardar atributos en el objeto
        self.user_ids = unique_users
        self.product_ids = unique_products
        self.user_item_matrix = matrix
        self.user_similarity = user_sim
        self.user_to_idx = user_to_idx
        self.prod_to_idx = prod_to_idx

        # Serializar modelo guardado en disco
        state = {
            "user_ids": self.user_ids,
            "product_ids": self.product_ids,
            "user_item_matrix": self.user_item_matrix,
            "user_similarity": self.user_similarity,
            "user_to_idx": self.user_to_idx,
            "prod_to_idx": self.prod_to_idx,
            "productos_map": self.productos_map,
            "popular_products": self.popular_products
        }

        joblib.dump(state, self.model_path)
        print(f"[Recomendador ML] Modelo de Scikit-Learn entrenado y guardado exitosamente en:\n {self.model_path}")
        return True

    def cargar_modelo(self):
        """Carga el modelo serializado desde el archivo .joblib."""
        if os.path.exists(self.model_path):
            try:
                state = joblib.load(self.model_path)
                self.user_ids = state.get("user_ids", [])
                self.product_ids = state.get("product_ids", [])
                self.user_item_matrix = state.get("user_item_matrix")
                self.user_similarity = state.get("user_similarity")
                self.user_to_idx = state.get("user_to_idx", {})
                self.prod_to_idx = state.get("prod_to_idx", {})
                self.productos_map = state.get("productos_map", {})
                self.popular_products = state.get("popular_products", [])
                return True
            except Exception as e:
                print(f"[Recomendador ML] No se pudo cargar modelo guardado: {e}")
        return False

    def _construir_fallback_popular(self, productos):
        self.productos_map = {p["id"]: p for p in productos}
        self.popular_products = [p["id"] for p in productos]

    def obtener_recomendaciones(self, cliente_id, top_n=3, excluir_comprados=False):
        """
        Genera sugerencias de productos para un cliente dado.
        Retorna lista de diccionarios lista para JSON / API Web.
        """
        # Asegurar mapa de productos actualizado desde la base de datos si falta alguno
        if not self.productos_map:
            prods = self.db.listar_productos()
            self.productos_map = {p["id"]: p for p in prods}

        # 1. Caso Cold-Start: Cliente no existe en el entrenamiento o sin matriz
        if (self.user_similarity is None) or (cliente_id not in getattr(self, "user_to_idx", {})):
            return self._recomendar_mas_populares(top_n=top_n, motivo="Producto popular entre los clientes de la tienda")

        u_idx = self.user_to_idx[cliente_id]
        user_vector = self.user_item_matrix[u_idx]

        # 2. Calcular puntuación para cada producto basada en la similitud de otros usuarios
        sim_scores = self.user_similarity[u_idx] # Lista de similitud con cada usuario
        
        # Evitar división por cero
        sim_sum = np.sum(sim_scores)
        if sim_sum == 0:
            return self._recomendar_mas_populares(top_n=top_n, motivo="Popular de la tienda")

        # Vector de predicción de interés por producto: sum(similitud_v * compras_v_prod)
        scores = np.dot(sim_scores, self.user_item_matrix) / (sim_sum + 1e-9)

        # Si se desea excluir productos que el cliente YA compró
        if excluir_comprados:
            scores[user_vector > 0] = -1.0

        # Ordenar productos por puntuación descendente
        ranked_indices = np.argsort(scores)[::-1]

        recomendaciones = []
        for idx in ranked_indices:
            p_id = self.product_ids[idx]
            score_val = float(scores[idx])
            
            if score_val <= 0 and len(recomendaciones) >= top_n:
                break

            p_info = self.productos_map.get(p_id)
            if p_info:
                motivo = "Recomendado por clientes con patrones de compra similares" if user_vector[idx] == 0 else "Tu producto frecuente preferido"
                recomendaciones.append({
                    "producto_id": p_info["id"],
                    "codigo_barras": p_info["codigo_barras"],
                    "nombre": p_info["nombre"],
                    "categoria": p_info["categoria"],
                    "precio": float(p_info["precio"]),
                    "score": round(score_val, 3),
                    "motivo": motivo
                })

            if len(recomendaciones) >= top_n:
                break

        # Si no alcanzaron suficientes recomendaciones, rellenar con populares
        if len(recomendaciones) < top_n:
            populares_fallback = self._recomendar_mas_populares(top_n=top_n, motivo="Tendencia popular en la tienda")
            ids_actuales = set(r["producto_id"] for r in recomendaciones)
            for p_pop in populares_fallback:
                if p_pop["producto_id"] not in ids_actuales:
                    recomendaciones.append(p_pop)
                    if len(recomendaciones) >= top_n:
                        break

        return recomendaciones[:top_n]

    def _recomendar_mas_populares(self, top_n=3, motivo="Producto más vendido de la tienda"):
        recomendaciones = []
        for p_id in self.popular_products:
            p_info = self.productos_map.get(p_id)
            if p_info:
                recomendaciones.append({
                    "producto_id": p_info["id"],
                    "codigo_barras": p_info["codigo_barras"],
                    "nombre": p_info["nombre"],
                    "categoria": p_info["categoria"],
                    "precio": float(p_info["precio"]),
                    "score": 1.0,
                    "motivo": motivo
                })
            if len(recomendaciones) >= top_n:
                break
        return recomendaciones


if __name__ == "__main__":
    print("=" * 65)
    print("   ENTRENANDO MODELO DE RECOMENDACION CON SCIKIT-LEARN")
    print("=" * 65)
    rec = RecomendadorProductos()
    exito = rec.entrenar_modelo()
    
    if exito:
        print("\nPrueba de recomendación para Cliente ID 1:")
        recs = rec.obtener_recomendaciones(cliente_id=1, top_n=3)
        for i, r in enumerate(recs, 1):
            print(f"  {i}. {r['nombre']} (${r['precio']}) - Motivo: {r['motivo']} (Score: {r['score']})")

        print("\nPrueba Cold-Start (Cliente nuevo / desconocido ID 999):")
        recs_cold = rec.obtener_recomendaciones(cliente_id=999, top_n=3)
        for i, r in enumerate(recs_cold, 1):
            print(f"  {i}. {r['nombre']} (${r['precio']}) - Motivo: {r['motivo']}")
