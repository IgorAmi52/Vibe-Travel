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
        destination = _normalize_string(state.get("destination_place"))
        if not destination:
            places = [place for place in (intent.get("places") or []) if _normalize_string(place)]
            destination = places[0] if places else None

        check_in_raw = _normalize_string(intent.get("start_date"))
        check_out_raw = _normalize_string(intent.get("end_date"))
        if not check_in_raw or not check_out_raw:
            check_in_raw, check_out_raw = _fallback_dates_from_flights(state.get("flight_results") or [])
        if not destination or not check_in_raw or not check_out_raw:
            return _noop_update(state)

        try:
            check_in = date.fromisoformat(check_in_raw)
            check_out = date.fromisoformat(check_out_raw)
        except ValueError:
            return {
                "hotel_results": [],
                "grouped_results": [],
                "status": "needs_clarification",
                "next_step": "search_hotels",
                "needs_clarification": True,
                "clarification_prompt": "I need valid hotel dates in YYYY-MM-DD format to rank hotels.",
            }

        vibe_query = _build_vibe_query(state.get("user_query"), intent.get("vibe"))
        logger.info(
            "Starting hotel ranking: destination=%s check_in=%s check_out=%s flight_count=%d",
            destination,
            check_in.isoformat(),
            check_out.isoformat(),
            len(state.get("flight_results") or []),
        )
        hotel_ranking_service = self.hotel_ranking_service_factory()
        try:
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
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_hotels",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"I couldn't rank hotels for {destination} ({exc}). "
                        "Could you refine the destination or dates?"
                    ),
                }

            hotel_results = [_serialize_scored_hotel(item) for item in ranked_hotels[: self.limit]]
            logger.info(
                "Hotel ranking completed: destination=%s ranked=%d returned=%d",
                destination,
                len(ranked_hotels),
                len(hotel_results),
            )
            if not hotel_results:
                logger.warning("Hotel ranking produced no usable hotels for destination=%s", destination)
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_hotels",
                    "needs_clarification": True,
                    "clarification_prompt": f"I couldn't find ranked hotels for {destination}.",
                }

            return {
                "destination_place": destination,
                "hotel_results": hotel_results,
                "grouped_results": [],
                "status": "hotels_ranked",
                "next_step": "group_results",
                "needs_clarification": False,
                "clarification_prompt": None,
            }
        finally:
            await hotel_ranking_service.close()


def _serialize_scored_hotel(scored_hotel: Any) -> Dict[str, Any]:
    hotel = scored_hotel.hotel
    return {
        "hotel_id": hotel.hotel_id,
        "name": hotel.name,
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
