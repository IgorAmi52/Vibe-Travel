from abc import ABC, abstractmethod

from core.models.hotel import Hotel


class HotelEmbeddingService(ABC):

    @abstractmethod
    def build_text_blobs(self, hotels: list[Hotel]) -> list[str]:
        """Produce a single text representation per hotel suitable for embedding."""

    @abstractmethod
    async def embed_query_and_hotels(
        self, vibe_query: str, hotel_blobs: list[str]
    ) -> tuple[list[float], list[list[float]]]:
        """Embed the vibe query and all hotel blobs in a single batch."""
