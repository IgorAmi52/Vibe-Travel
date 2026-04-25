import logging

from core.api.embed_provider import EmbedProvider
from core.models.hotel import Hotel
from core.services.hotel_embedding_service import HotelEmbeddingService

logger = logging.getLogger(__name__)

MAX_REVIEWS_FOR_EMBEDDING = 5


class HotelEmbeddingServiceImpl(HotelEmbeddingService):

    def __init__(self, embed_provider: EmbedProvider) -> None:
        self._embed_provider = embed_provider

    def build_text_blobs(self, hotels: list[Hotel]) -> list[str]:
        blobs: list[str] = []
        for hotel in hotels:
            parts: list[str] = []
            if hotel.description:
                parts.append(hotel.description)
            if hotel.amenities:
                parts.append(" ".join(hotel.amenities))
            parts.extend(hotel.reviews[:MAX_REVIEWS_FOR_EMBEDDING])

            blob = " ".join(parts).strip()
            if not blob:
                logger.warning("Empty text blob for hotel %s — no vibe signal available", hotel.hotel_id)
            blobs.append(blob)
        return blobs

    async def embed_query_and_hotels(
        self, vibe_query: str, hotel_blobs: list[str]
    ) -> tuple[list[float], list[list[float]]]:
        all_texts = [vibe_query] + hotel_blobs
        embeddings = await self._embed_provider.embed(all_texts)
        query_vector = embeddings[0]
        hotel_vectors = embeddings[1:]
        return query_vector, hotel_vectors
