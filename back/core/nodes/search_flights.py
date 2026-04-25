from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List

from core.flights import (
    FlightChainService,
    FlightLegChain,
    FlightSearchParams,
    FlightSegment,
    RoundTripChainResult,
)
from core.state import TripPlannerGraphState


@dataclass
class SearchFlightsNode:
    flight_service: FlightChainService
    limit: int = 10

    def __call__(self, state: TripPlannerGraphState) -> Dict[str, Any]:
        return asyncio.run(self._execute(state))

    async def _execute(self, state: TripPlannerGraphState) -> Dict[str, Any]:
        origin_iata = _normalize_search_value(state.get("origin_iata")) or "BCN"
        destination_iata = _normalize_search_value(state.get("destination_iata"))
        intent = state.get("trip_intent") or {}
        places = [place for place in (intent.get("places") or []) if _normalize_search_value(place)]
        departure_date_str = intent.get("start_date")
        return_date_str = intent.get("end_date")
        person_count = int(state.get("person_count") or intent.get("person_count") or 1)

        try:
            if not destination_iata and places:
                destination_iata, _ = await self._resolve_first_iata(places)

            if not destination_iata and places:
                attempted_places = ", ".join(places)
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "origin_iata": origin_iata,
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"I couldn't resolve an airport for any of these places: {attempted_places}. "
                        "Could you specify a nearby airport or another destination?"
                    ),
                }

            try:
                indicative = await self.flight_service.get_indicative_anywhere(
                    origin_iata=origin_iata,
                    destination_iata=destination_iata,
                    outbound_date=departure_date_str,
                    return_date=return_date_str,
                )
            except Exception as exc:
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"Indicative flight search failed ({exc}). "
                        "Could you check your dates or try a different destination?"
                    ),
                }

            if not isinstance(indicative, dict):
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        "Indicative flight search did not return usable results. "
                        "Could you try a different origin airport or travel month?"
                    ),
                }

            quotes = list(indicative.get("quotes") or [])
            if not quotes:
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        "No indicative destinations found for your search. "
                        "Could you try different dates or a nearby airport?"
                    ),
                }

            has_full_dates = bool(destination_iata and departure_date_str and return_date_str)
            return {
                "flight_results": quotes,
                "origin_iata": origin_iata,
                "destination_iata": destination_iata,
                "person_count": person_count,
                "status": "flights_ready" if has_full_dates else "indicative_flights_ready",
                "next_step": (
                    "search_hotels"
                    if has_full_dates
                    else ("select_dates" if destination_iata else "select_destination")
                ),
                "needs_clarification": False,
                "clarification_prompt": None,
            }
        finally:
            await self.flight_service.provider.close()

    async def _resolve_iata(self, search_term: str) -> str | None:
        return await self.flight_service.resolve_iata_code(search_term)

    async def _resolve_first_iata(self, places: List[str]) -> tuple[str | None, str | None]:
        for place in places:
            resolved_iata = await self._resolve_iata(place)
            if resolved_iata:
                return resolved_iata, place
        return None, None


def _chain_to_dict(chain: RoundTripChainResult) -> Dict[str, Any]:
    return {
        "itinerary_id": chain.itinerary_id,
        "price_amount": chain.price_amount,
        "price_currency": chain.price_currency,
        "agent_name": chain.agent_name,
        "deep_link": chain.deep_link,
        "validating_carriers": list(chain.validating_carriers),
        "outbound": _leg_to_dict(chain.outbound_chain),
        "inbound": _leg_to_dict(chain.inbound_chain),
    }


def _leg_to_dict(leg: FlightLegChain) -> Dict[str, Any]:
    return {
        "leg_id": leg.leg_id,
        "origin_iata": leg.origin_iata,
        "destination_iata": leg.destination_iata,
        "departure_at": leg.departure_at,
        "arrival_at": leg.arrival_at,
        "duration_minutes": leg.duration_minutes,
        "stop_count": leg.stop_count,
        "segments": [_segment_to_dict(s) for s in leg.segments],
    }


def _segment_to_dict(seg: FlightSegment) -> Dict[str, Any]:
    return {
        "origin_iata": seg.origin_iata,
        "destination_iata": seg.destination_iata,
        "departure_at": seg.departure_at,
        "arrival_at": seg.arrival_at,
        "marketing_carrier": seg.marketing_carrier,
        "flight_number": seg.flight_number,
        "duration_minutes": seg.duration_minutes,
    }


def _normalize_search_value(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
