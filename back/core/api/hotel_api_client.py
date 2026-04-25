from abc import ABC, abstractmethod
from datetime import date

from core.models.hotel import Destination, HotelContent, HotelReview, HotelSearchResult


class HotelApiClient(ABC):

    @abstractmethod
    async def autosuggest(self, search_term: str) -> list[Destination]:
        """Resolve a destination name to entity IDs."""

    @abstractmethod
    async def indicative_search(
        self,
        entity_id: str,
        check_in: date,
        check_out: date,
        currency: str = "USD",
    ) -> list[HotelSearchResult]:
        """Search hotels for a destination + date range. Returns hotels with pricing."""

    @abstractmethod
    async def get_content(self, hotel_ids: list[str]) -> list[HotelContent]:
        """Fetch static content (description, amenities, ratings) for given hotel IDs."""

    @abstractmethod
    async def get_description(self, hotel_id: str) -> str | None:
        """Fetch the narrative property description for a single hotel."""

    @abstractmethod
    async def get_reviews(self, hotel_id: str, limit: int = 30) -> list[HotelReview]:
        """Fetch guest reviews for a single hotel."""
