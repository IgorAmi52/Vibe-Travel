import math

from core.services.similarity_service import SimilarityService


class CosineSimilarityService(SimilarityService):

    def compute_similarity(
        self, query_vector: list[float], candidate_vectors: list[list[float]]
    ) -> list[float]:
        query_norm = _vector_norm(query_vector)
        if query_norm == 0.0:
            return [0.0 for _ in candidate_vectors]

        similarities: list[float] = []
        for candidate in candidate_vectors:
            candidate_norm = _vector_norm(candidate)
            if candidate_norm == 0.0:
                similarities.append(0.0)
                continue
            numerator = sum(left * right for left, right in zip(query_vector, candidate))
            similarities.append(numerator / max(query_norm * candidate_norm, 1e-10))
        return similarities


def _vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))
