import logging
from typing import Any

from httpx import HTTPStatusError

from back.clients.api_connector import ApiConnector
from back.core.api.hotel_api_client import HotelApiClient
from back.core.models.hotel import Destination, GeoCoordinates

logger = logging.getLogger(__name__)


class SkyscannerHotelClient(HotelApiClient):

    def __init__(
        self,
        api_connector: ApiConnector,
        market: str = "UK",
        locale: str = "en-GB",
    ) -> None:
        self._api = api_connector
        self._market = market
        self._locale = locale

    async def autosuggest(self, search_term: str) -> list[Destination]:
        payload = {
            "query": {
                "market": self._market,
                "locale": self._locale,
                "searchTerm": search_term,
                "includedEntityTypes": ["PLACE_TYPE_HOTEL"],
            }
        }
        try:
            response = await self._api.post("/apiservices/v3/autosuggest/hotels", json=payload)
        except HTTPStatusError as exc:
            logger.error("Autosuggest failed for '%s': %s", search_term, exc)
            if exc.response.status_code == 429:
                raise
            return []

        return self._parse_autosuggest(response.json())

    @staticmethod
    def _parse_location(raw: str) -> GeoCoordinates | None:
        parts = raw.split(",")
        if len(parts) != 2:
            return None
        try:
            return GeoCoordinates(latitude=float(parts[0]), longitude=float(parts[1]))
        except ValueError:
            return None

    @staticmethod
    def _parse_autosuggest(data: Any) -> list[Destination]:
        results: list[Destination] = []
        for item in data.get("places", []):
            location = None
            if raw_loc := item.get("location"):
                location = SkyscannerHotelClient._parse_location(raw_loc)

            results.append(Destination(
                entity_id=item["entityId"],
                name=item["name"],
                hierarchy=item.get("hierarchy", ""),
                location=location,
            ))
        return results
