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
                destination_iata = await self._resolve_iata(places[0])

            if not destination_iata and places:
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "origin_iata": origin_iata,
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"I couldn't resolve an airport for {places[0]}. "
                        "Could you specify a nearby airport or another destination?"
                    ),
                }

            if not destination_iata or not departure_date_str or not return_date_str:
                try:
                    indicative = await self.flight_service.get_indicative_anywhere(
                        origin_iata=origin_iata,
                        destination_iata=destination_iata,
                        outbound_date=departure_date_str,
                    )
                except Exception as exc:
                    return {
                        "status": "needs_clarification",
                        "next_step": "search_flights",
                        "needs_clarification": True,
                        "clarification_prompt": (
                            f"Indicative flight search failed ({exc}). "
                            "Could you check your departure date or try a different origin airport?"
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

                return {
                    "flight_results": quotes,
                    "origin_iata": origin_iata,
                    "destination_iata": destination_iata,
                    "person_count": person_count,
                    "status": "indicative_flights_ready",
                    "next_step": "select_dates" if destination_iata else "select_destination",
                    "needs_clarification": False,
                    "clarification_prompt": None,
                }

            try:
                params = FlightSearchParams(
                    origin_iata=origin_iata,
                    destination_iata=destination_iata,
                    departure_date=date.fromisoformat(departure_date_str),
                    return_date=date.fromisoformat(return_date_str),
                    adults=person_count,
                )
                results = await self.flight_service.get_roundtrip_chains(params, limit=self.limit)
            except Exception as exc:
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"Flight search failed ({exc}). "
                        "Could you check your dates or try a different destination?"
                    ),
                }

            if not results:
                return {
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        "No flights found for your search. "
                        "Could you try different dates or a nearby airport?"
                    ),
                }

            return {
                "flight_results": [_chain_to_dict(r) for r in results],
                "origin_iata": origin_iata,
                "destination_iata": destination_iata,
                "person_count": person_count,
                "status": "flights_ready",
                "next_step": "search_hotels",
                "needs_clarification": False,
                "clarification_prompt": None,
            }
        finally:
            await self.flight_service.provider.close()

    async def _resolve_iata(self, search_term: str) -> str | None:
        return await self.flight_service.resolve_iata_code(search_term)


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
