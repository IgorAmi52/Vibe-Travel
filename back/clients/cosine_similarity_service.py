import numpy as np

from core.services.similarity_service import SimilarityService


class CosineSimilarityService(SimilarityService):

    def compute_similarity(
        self, query_vector: list[float], candidate_vectors: list[list[float]]
    ) -> list[float]:
        query = np.array(query_vector)
        candidates = np.array(candidate_vectors)
        dot_products = candidates @ query
        norms = np.linalg.norm(candidates, axis=1) * np.linalg.norm(query)
        norms = np.maximum(norms, 1e-10)
        return (dot_products / norms).tolist()
