from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable, Dict

from core.services.hotel_ranking_service import HotelRankingService
from core.state import TripPlannerGraphState

logger = logging.getLogger(__name__)
DEFAULT_STAY_DAYS = 4


@dataclass
class SearchHotelsNode:
    hotel_ranking_service_factory: Callable[[], HotelRankingService]
    limit: int = 5

    def __call__(self, state: TripPlannerGraphState) -> Dict[str, Any]:
        return asyncio.run(self._execute(state))

    async def _execute(self, state: TripPlannerGraphState) -> Dict[str, Any]:
        if state.get("status") not in {"flights_ready", "indicative_flights_ready"}:
            return _noop_update(state)

        intent = state.get("trip_intent") or {}
        destinations = _candidate_destinations(state)
        if not destinations:
            return _noop_update(state)

        vibe_query = _build_vibe_query(state.get("user_query"), intent.get("vibe"))
        try:
            hotel_ranking_service = self.hotel_ranking_service_factory()
        except Exception:
            logger.exception("Hotel ranking service could not be initialized")
            return _noop_update(state)
        try:
            hotel_results = []
            attempted_rankings = 0
            failed_rankings = 0
            for destination in destinations:
                check_in_raw, check_out_raw = _resolve_dates_for_destination(state, destination)
                if not check_in_raw or not check_out_raw:
                    continue

                try:
                    check_in = date.fromisoformat(check_in_raw)
                    check_out = date.fromisoformat(check_out_raw)
                except ValueError:
                    continue

                logger.info(
                    "Starting hotel ranking: destination=%s check_in=%s check_out=%s",
                    destination,
                    check_in.isoformat(),
                    check_out.isoformat(),
                )
                attempted_rankings += 1
                try:
                    ranked_hotels = await hotel_ranking_service.rank_hotels(
                        vibe_query=vibe_query,
                        destination=destination,
                        check_in=check_in,
                        check_out=check_out,
                    )
                except Exception as exc:
                    logger.exception(
                        "Hotel ranking failed: destination=%s check_in=%s check_out=%s error=%s",
                        destination,
                        check_in.isoformat(),
                        check_out.isoformat(),
                        exc,
                    )
                    failed_rankings += 1
                    continue

                destination_hotels = [
                    _serialize_scored_hotel(item, destination_place=destination)
                    for item in ranked_hotels[: self.limit]
                ]
                logger.info(
                    "Hotel ranking completed: destination=%s ranked=%d returned=%d",
                    destination,
                    len(ranked_hotels),
                    len(destination_hotels),
                )
                hotel_results.extend(destination_hotels)

            if not hotel_results:
                if attempted_rankings and failed_rankings == attempted_rankings:
                    return _noop_update(state)
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_hotels",
                    "needs_clarification": True,
                    "clarification_prompt": "I couldn't rank hotels for any of the candidate destinations.",
                }

            return {
                "hotel_results": hotel_results,
                "grouped_results": [],
                "status": "hotels_ranked",
                "next_step": "group_results",
                "needs_clarification": False,
                "clarification_prompt": None,
            }
        finally:
            await hotel_ranking_service.close()


def _serialize_scored_hotel(scored_hotel: Any, *, destination_place: str | None = None) -> Dict[str, Any]:
    hotel = scored_hotel.hotel
    return {
        "hotel_id": hotel.hotel_id,
        "name": hotel.name,
        "destination_place": destination_place,
        "price": {
            "amount": hotel.price,
            "currency": hotel.currency,
        },
        "description": hotel.description,
        "amenities": list(hotel.amenities),
        "star_rating": hotel.star_rating,
        "guest_rating": hotel.guest_rating,
        "accommodation_type": hotel.accommodation_type,
        "images": list(hotel.images),
        "scores": {
            "vibe_similarity": scored_hotel.vibe_similarity,
            "price_score": scored_hotel.price_score,
            "guest_rating_score": scored_hotel.guest_rating_score,
            "composite_score": scored_hotel.composite_score,
        },
    }


def _build_vibe_query(user_query: Any, vibe: Any) -> str:
    if isinstance(vibe, list):
        vibe_text = ", ".join(str(item).strip() for item in vibe if str(item).strip())
    else:
        vibe_text = _normalize_string(vibe) or ""

    user_query_text = _normalize_string(user_query) or ""
    return vibe_text or user_query_text or "comfortable hotel"


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _fallback_dates_from_flights(flight_results: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    if not flight_results:
        return None, None

    first_flight = flight_results[0]
    outbound = _normalize_string(first_flight.get("outbound_datetime"))
    inbound = _normalize_string(first_flight.get("inbound_datetime"))
    check_in = _extract_iso_date(outbound)
    check_out = _extract_iso_date(inbound)
    if check_in and not check_out:
        try:
            check_out = (date.fromisoformat(check_in) + timedelta(days=DEFAULT_STAY_DAYS)).isoformat()
        except ValueError:
            return check_in, None
    return check_in, check_out


def _candidate_destinations(state: TripPlannerGraphState) -> list[str]:
    destinations: list[str] = []
    for flight in state.get("flight_results") or []:
        destination = _normalize_string(flight.get("destination_place"))
        if destination and destination not in destinations:
            destinations.append(destination)

    if destinations:
        return destinations

    explicit_destination = _normalize_string(state.get("destination_place"))
    if explicit_destination:
        return [explicit_destination]

    trip_intent = state.get("trip_intent") or {}
    for place in trip_intent.get("places") or []:
        normalized = _normalize_string(place)
        if normalized and normalized not in destinations:
            destinations.append(normalized)
    return destinations


def _resolve_dates_for_destination(
    state: TripPlannerGraphState,
    destination: str,
) -> tuple[str | None, str | None]:
    intent = state.get("trip_intent") or {}
    check_in_raw = _normalize_string(intent.get("start_date"))
    check_out_raw = _normalize_string(intent.get("end_date"))
    if check_in_raw and check_out_raw:
        return check_in_raw, check_out_raw

    destination_flights = [
        flight
        for flight in (state.get("flight_results") or [])
        if _normalize_string(flight.get("destination_place")) == destination
    ]
    if not destination_flights:
        destination_flights = list(state.get("flight_results") or [])
    return _fallback_dates_from_flights(destination_flights)


def _extract_iso_date(datetime_value: str | None) -> str | None:
    if not datetime_value:
        return None
    if "T" in datetime_value:
        return datetime_value.split("T", 1)[0]
    return datetime_value[:10] if len(datetime_value) >= 10 else None


def _noop_update(state: TripPlannerGraphState) -> Dict[str, Any]:
    return {
        "hotel_results": [],
        "grouped_results": [],
        "status": state.get("status", "received"),
        "next_step": state.get("next_step"),
    }
