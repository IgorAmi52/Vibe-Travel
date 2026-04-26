from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from httpx import HTTPStatusError

from clients.api_connector import ApiConnector
from clients.booking_parsers import parse_description, parse_destinations, parse_hotel_detail, parse_hotel_search, parse_reviews
from core.api.hotel_api_client import HotelApiClient
from core.models.hotel import Destination, HotelContent, HotelReview, HotelSearchResult

logger = logging.getLogger(__name__)

SEARCH_TYPE_CITY = "city"
REVIEW_SORT_MOST_RELEVANT = "SORT_MOST_RELEVANT"
_AUTH_ERROR_CODES = {401, 403, 429}


class BookingComClient(HotelApiClient):

    def __init__(
        self,
        api_connector: ApiConnector,
        language_code: str = "en-us",
        currency_code: str = "USD",
    ) -> None:
        self._api = api_connector
        self._language_code = language_code
        self._currency_code = currency_code

    def _should_raise(self, exc: HTTPStatusError) -> bool:
        return exc.response.status_code in _AUTH_ERROR_CODES

    async def autosuggest(self, search_term: str) -> list[Destination]:
        try:
            response = await self._api.get(
                "/api/v1/hotels/searchDestination",
                params={"query": search_term},
            )
        except HTTPStatusError as exc:
            logger.error("Destination search failed for '%s': %s", search_term, exc)
            if self._should_raise(exc):
                raise
            return []

        return parse_destinations(response.json())

    async def indicative_search(
        self,
        entity_id: str,
        check_in: date,
        check_out: date,
        currency: str = "USD",
    ) -> list[HotelSearchResult]:
        params = {
            "dest_id": entity_id,
            "search_type": SEARCH_TYPE_CITY,
            "arrival_date": check_in.isoformat(),
            "departure_date": check_out.isoformat(),
            "adults": 2,
            "room_qty": 1,
            "currency_code": currency or self._currency_code,
            "languagecode": self._language_code,
        }
        try:
            response = await self._api.get("/api/v1/hotels/searchHotels", params=params)
        except HTTPStatusError as exc:
            logger.error("Hotel search failed for dest '%s': %s", entity_id, exc)
            if self._should_raise(exc):
                raise
            return []

        return parse_hotel_search(response.json())

    async def get_content(self, hotel_ids: list[str]) -> list[HotelContent]:
        default_arrival = (date.today() + timedelta(days=30)).isoformat()
        default_departure = (date.today() + timedelta(days=31)).isoformat()

        async def fetch_one(hotel_id: str) -> HotelContent | None:
            params = {
                "hotel_id": hotel_id,
                "arrival_date": default_arrival,
                "departure_date": default_departure,
                "adults": 1,
                "room_qty": 1,
                "currency_code": self._currency_code,
                "languagecode": self._language_code,
            }
            try:
                response = await self._api.get("/api/v1/hotels/getHotelDetails", params=params)
            except HTTPStatusError as exc:
                logger.error("Content fetch failed for hotel '%s': %s", hotel_id, exc)
                if self._should_raise(exc):
                    raise
                return None
            return parse_hotel_detail(response.json())

        results = await asyncio.gather(*(fetch_one(hid) for hid in hotel_ids))
        return [r for r in results if r is not None]

    async def get_description(self, hotel_id: str) -> str | None:
        params = {
            "hotel_id": hotel_id,
            "languagecode": self._language_code,
        }
        try:
            response = await self._api.get(
                "/api/v1/hotels/getDescriptionAndInfo", params=params,
            )
        except HTTPStatusError as exc:
            logger.error("Description fetch failed for hotel '%s': %s", hotel_id, exc)
            if self._should_raise(exc):
                raise
            return None

        return parse_description(response.json())

    async def get_reviews(self, hotel_id: str, limit: int = 15) -> list[HotelReview]:
        all_reviews: list[HotelReview] = []
        page = 0

        while len(all_reviews) < limit:
            params = {
                "hotel_id": hotel_id,
                "languagecode": self._language_code,
                "sort_type": REVIEW_SORT_MOST_RELEVANT,
                "page": page,
            }
            try:
                response = await self._api.get("/api/v1/hotels/getHotelReviews", params=params)
            except HTTPStatusError as exc:
                logger.error("Reviews fetch failed for hotel '%s': %s", hotel_id, exc)
                if self._should_raise(exc):
                    raise
                break

            batch = parse_reviews(response.json())
            if not batch:
                break

            all_reviews.extend(batch)
            page += 1

        return all_reviews[:limit]

    async def close(self) -> None:
        await self._api.close()
