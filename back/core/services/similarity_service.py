from abc import ABC, abstractmethod


class SimilarityService(ABC):
    @abstractmethod
    def compute_similarity(
        self, query_vector: list[float], candidate_vectors: list[list[float]]
    ) -> list[float]:
        """Return similarity scores between query and each candidate."""
