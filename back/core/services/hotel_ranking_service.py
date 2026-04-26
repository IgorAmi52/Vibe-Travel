from __future__ import annotations

import asyncio
import logging
from datetime import date

from core.api.hotel_api_client import HotelApiClient
from core.models.hotel import Hotel, HotelContent, HotelReview, HotelSearchResult, ScoredHotel
from core.services.hotel_embedding_service import HotelEmbeddingService
from core.services.similarity_service import SimilarityService

logger = logging.getLogger(__name__)

DEFAULT_VIBE_WEIGHT = 0.6
DEFAULT_PRICE_WEIGHT = 0.2
DEFAULT_RATING_WEIGHT = 0.2
MAX_REVIEWS_TO_FETCH = 15
# Destination types Booking.com supports for hotel search, ordered by how well
# they typically match a user-facing place name (cities are tightest scope).
_ACCEPTED_DESTINATION_TYPES: tuple[str, ...] = (
    "city",
    "region",
    "district",
    "landmark",
    "country",
)


class HotelRankingService:

    def __init__(
        self,
        hotel_api: HotelApiClient,
        embedding_service: HotelEmbeddingService,
        similarity_service: SimilarityService,
        vibe_weight: float = DEFAULT_VIBE_WEIGHT,
        price_weight: float = DEFAULT_PRICE_WEIGHT,
        rating_weight: float = DEFAULT_RATING_WEIGHT,
    ) -> None:
        self._hotel_api = hotel_api
        self._embedding_service = embedding_service
        self._similarity_service = similarity_service
        self._w_vibe = vibe_weight
        self._w_price = price_weight
        self._w_rating = rating_weight

    async def rank_hotels(
        self,
        vibe_query: str,
        destination: str,
        check_in: date,
        check_out: date,
        currency: str = "USD",
    ) -> list[ScoredHotel]:
        entity_id, search_type = await self._resolve_destination_entity(destination)

        search_results = await self._hotel_api.indicative_search(
            entity_id=resolved_destination.entity_id,
            check_in=check_in,
            check_out=check_out,
            search_type=resolved_destination.dest_type or "city",
            currency=currency,
            search_type=search_type,
        )
        if not search_results:
            raise ValueError(
                "No hotels found for "
                f"'{destination}' (entity={resolved_destination.entity_id}, type={resolved_destination.dest_type})"
            )

        # Booking.com's searchHotels still returns properties that have no
        # availability for the requested window (priceBreakdown.grossPrice is
        # null). Including them produces deal links that land on a "no
        # availability for these dates" page, which is bad UX. Drop them here
        # so the user only sees genuinely bookable options.
        bookable_results = [r for r in search_results if r.price is not None]
        dropped = len(search_results) - len(bookable_results)
        if dropped:
            logger.info(
                "Dropped %d/%d hotels with no availability for %s → %s",
                dropped,
                len(search_results),
                check_in.isoformat(),
                check_out.isoformat(),
            )
        if not bookable_results:
            raise ValueError(
                f"No hotels with availability for '{destination}' "
                f"between {check_in.isoformat()} and {check_out.isoformat()}"
            )

        hotel_ids = [h.hotel_id for h in bookable_results]
        logger.info("Found %d bookable hotels for entity '%s'", len(hotel_ids), entity_id)

        contents, descriptions, reviews_by_hotel = await self._fetch_hotel_data(hotel_ids)
        hotels = self._build_hotels(bookable_results, contents, descriptions, reviews_by_hotel)
        similarities = await self._compute_similarities(vibe_query, hotels)

        return self._score_and_rank(hotels, similarities)

    async def _resolve_destination_entity(self, destination: str) -> tuple[str, str]:
        destinations = await self._hotel_api.autosuggest(destination)
        if not destinations:
            raise ValueError(f"No destinations found for '{destination}'")

        match = None
        for accepted_type in _ACCEPTED_DESTINATION_TYPES:
            match = next((d for d in destinations if d.dest_type == accepted_type), None)
            if match:
                break

        if not match:
            raise ValueError(
                f"No usable destination found for '{destination}'. "
                f"Got: {[(d.name, d.dest_type) for d in destinations]}"
            )

        logger.info(
            "Resolved '%s' → %s (entity=%s, type=%s)",
            destination,
            match.name,
            match.entity_id,
            match.dest_type,
        )
        return match.entity_id, match.dest_type

    async def _fetch_hotel_data(
        self, hotel_ids: list[str],
    ) -> tuple[list[HotelContent], dict[str, str | None], dict[str, list[HotelReview]]]:
        content_task = self._hotel_api.get_content(hotel_ids)
        description_tasks = [self._hotel_api.get_description(hid) for hid in hotel_ids]
        review_tasks = [
            self._hotel_api.get_reviews(hid, limit=MAX_REVIEWS_TO_FETCH)
            for hid in hotel_ids
        ]

        results = await asyncio.gather(
            content_task, *description_tasks, *review_tasks, return_exceptions=True,
        )
        content_result = results[0]
        desc_results = results[1:1 + len(hotel_ids)]
        review_results = results[1 + len(hotel_ids):]

        contents: list[HotelContent] = content_result if not isinstance(content_result, BaseException) else []
        if isinstance(content_result, BaseException):
            logger.warning("Content fetch failed: %s", content_result)

        descriptions_by_hotel: dict[str, str | None] = {}
        for hid, result in zip(hotel_ids, desc_results):
            if isinstance(result, BaseException):
                logger.warning("Description fetch failed for %s: %s", hid, result)
                descriptions_by_hotel[hid] = None
            else:
                descriptions_by_hotel[hid] = result

        reviews_by_hotel: dict[str, list[HotelReview]] = {}
        for hid, result in zip(hotel_ids, review_results):
            if isinstance(result, BaseException):
                logger.warning("Reviews fetch failed for %s: %s", hid, result)
                reviews_by_hotel[hid] = []
            else:
                reviews_by_hotel[hid] = result

        return contents, descriptions_by_hotel, reviews_by_hotel

    @staticmethod
    def _build_hotels(
        search_results: list[HotelSearchResult],
        contents: list[HotelContent],
        descriptions_by_hotel: dict[str, str | None],
        reviews_by_hotel: dict[str, list[HotelReview]],
    ) -> list[Hotel]:
        content_map = {c.hotel_id: c for c in contents}
        hotels: list[Hotel] = []
        for result in search_results:
            hid = result.hotel_id
            content = content_map.get(hid)
            description = descriptions_by_hotel.get(hid)
            reviews = reviews_by_hotel.get(hid, [])
            review_texts = [r.content for r in reviews if r.content]

            images = result.photo_urls or (content.images if content else [])

            hotels.append(Hotel(
                hotel_id=hid,
                name=content.name if content else result.name,
                price=result.price.gross_amount if result.price else None,
                currency=result.price.currency if result.price else None,
                description=description,
                amenities=content.amenities if content else [],
                star_rating=content.star_rating if content else None,
                guest_rating=content.guest_rating if content else result.review_score,
                accommodation_type=content.accommodation_type if content else None,
                reviews=review_texts,
                images=images,
            ))
        return hotels

    async def _compute_similarities(
        self, vibe_query: str, hotels: list[Hotel]
    ) -> list[float]:
        blobs = self._embedding_service.build_text_blobs(hotels)
        query_vec, hotel_vecs = await self._embedding_service.embed_query_and_hotels(vibe_query, blobs)
        return self._similarity_service.compute_similarity(query_vec, hotel_vecs)

    def _score_and_rank(
        self, hotels: list[Hotel], similarities: list[float]
    ) -> list[ScoredHotel]:
        price_scores = self._normalize_price_scores(hotels)
        rating_scores = self._normalize_rating_scores(hotels)

        scored: list[ScoredHotel] = []
        for i, hotel in enumerate(hotels):
            vibe_sim = similarities[i]
            price_s = price_scores[i]
            rating_s = rating_scores[i]
            composite = (
                self._w_vibe * vibe_sim
                + self._w_price * price_s
                + self._w_rating * rating_s
            )
            scored.append(ScoredHotel(
                hotel=hotel,
                vibe_similarity=round(vibe_sim, 4),
                price_score=round(price_s, 4),
                guest_rating_score=round(rating_s, 4),
                composite_score=round(composite, 4),
            ))

        scored.sort(key=lambda s: s.composite_score, reverse=True)
        return scored

    async def close(self) -> None:
        await self._hotel_api.close()

    @staticmethod
    def _normalize_price_scores(hotels: list[Hotel]) -> list[float]:
        valid_prices = [h.price for h in hotels if h.price is not None and h.price > 0]
        if not valid_prices:
            return [0.5] * len(hotels)

        min_p, max_p = min(valid_prices), max(valid_prices)
        scores: list[float] = []
        for h in hotels:
            if h.price is None or h.price <= 0:
                scores.append(0.5)
            elif max_p == min_p:
                scores.append(1.0)
            else:
                scores.append(1.0 - (h.price - min_p) / (max_p - min_p))
        return scores

    @staticmethod
    def _normalize_rating_scores(hotels: list[Hotel]) -> list[float]:
        scores: list[float] = []
        for h in hotels:
            if h.guest_rating is not None:
                scores.append(min(max(h.guest_rating / 10.0, 0.0), 1.0))
            else:
                scores.append(0.5)
        return scores
