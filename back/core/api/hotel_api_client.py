from abc import ABC, abstractmethod

from back.core.models.hotel import Destination


class HotelApiClient(ABC):

    @abstractmethod
    async def autosuggest(self, search_term: str) -> list[Destination]:
        """Search for hotels matching the given term.

        Returns hotels ordered by relevance, each with an entity_id
        that can be used with other hotel API operations.
        """
