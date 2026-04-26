from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

from core.flights import (
    FlightChainService,
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
        destination_place = _normalize_search_value(state.get("destination_place"))
        destination_iata = _normalize_search_value(state.get("destination_iata"))
        intent = state.get("trip_intent") or {}
        places = [place for place in (intent.get("places") or []) if _normalize_search_value(place)]
        departure_date_str = intent.get("start_date")
        return_date_str = intent.get("end_date")
        person_count = int(state.get("person_count") or intent.get("person_count") or 1)

        try:
            resolved_destinations = await self._resolve_destinations(
                destination_iata=destination_iata,
                destination_place=destination_place,
                places=places,
            )

            if not resolved_destinations and places:
                attempted_places = ", ".join(places)
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "origin_iata": origin_iata,
                    "destination_place": destination_place,
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"I couldn't resolve an airport for any of these places: {attempted_places}. "
                        "Could you specify a nearby airport or another destination?"
                    ),
                }

            if not resolved_destinations and destination_iata:
                resolved_destinations = [(destination_place or destination_iata, destination_iata)]

            anywhere_search = not resolved_destinations and not destination_iata and not places
            if not resolved_destinations and not anywhere_search:
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "origin_iata": origin_iata,
                    "needs_clarification": True,
                    "clarification_prompt": (
                        "I need at least one destination to continue. "
                        "Could you specify a place or nearby airport?"
                    ),
                }

            primary_place = resolved_destinations[0][0] if resolved_destinations else destination_place
            primary_iata = resolved_destinations[0][1] if resolved_destinations else destination_iata
            has_full_dates = bool(departure_date_str and return_date_str)
            try:
                if destination_iata:
                    # Always query both directions for a known destination so both
                    # outbound and inbound legs carry dates (avoids "TBC" return).
                    quotes = list(
                        await self.flight_service.get_indicative_roundtrip(
                            origin_iata=origin_iata,
                            destination_iata=destination_iata,
                            departure_date=departure_date_str,
                            return_date=return_date_str,
                            limit=self.limit,
                        )
                    )
                else:
                    indicative = await self.flight_service.get_indicative_anywhere(
                        origin_iata=origin_iata,
                        destination_iata=destination_iata,
                        outbound_date=departure_date_str,
                        return_date=return_date_str,
                    )
                    if not isinstance(indicative, dict):
                        return {
                            "hotel_results": [],
                            "grouped_results": [],
                            "status": "needs_clarification",
                            "next_step": "search_flights",
                            "needs_clarification": True,
                            "clarification_prompt": (
                                "Indicative flight search did not return usable results. "
                                "Could you try a different origin airport or travel month?"
                            ),
                        }
                    quotes = list(indicative.get("quotes") or [])
            except Exception as exc:
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"Indicative flight search failed ({exc}). "
                        "Could you check your dates or try a different destination?"
                    ),
                }

            if not quotes:
                return {
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "search_flights",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        "No indicative destinations found for your search. "
                        "Could you try different dates or a nearby airport?"
                    ),
                }

            scaled_quotes = _scale_flight_prices(quotes, person_count)

            return {
                "flight_results": scaled_quotes,
                "hotel_results": [],
                "grouped_results": [],
                "origin_iata": origin_iata,
                "destination_place": primary_place,
                "destination_iata": primary_iata,
                "person_count": person_count,
                "status": "flights_ready" if has_full_dates else "indicative_flights_ready",
                "next_step": "search_hotels" if not anywhere_search else "select_destination",
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

    async def _resolve_destinations(
        self,
        *,
        destination_iata: str | None,
        destination_place: str | None,
        places: List[str],
    ) -> List[tuple[str, str]]:
        if destination_iata:
            return [(destination_place or (places[0] if places else destination_iata), destination_iata)]

        resolved: List[tuple[str, str]] = []
        seen_iatas: set[str] = set()
        for place in places:
            resolved_iata = await self._resolve_iata(place)
            if not resolved_iata or resolved_iata in seen_iatas:
                continue
            seen_iatas.add(resolved_iata)
            resolved.append((place, resolved_iata))
        return resolved


def _normalize_search_value(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _scale_flight_prices(quotes: List[Dict[str, Any]], person_count: int) -> List[Dict[str, Any]]:
    """Skyscanner indicative prices are per-person; scale to total for the group."""
    if person_count <= 1:
        return quotes
    scaled: List[Dict[str, Any]] = []
    for q in quotes:
        q = dict(q)
        price = q.get("price")
        if isinstance(price, dict) and price.get("amount") is not None:
            q["price"] = {**price, "amount": float(price["amount"]) * person_count}
        for leg_key in ("outbound", "inbound"):
            leg = q.get(leg_key)
            if isinstance(leg, dict):
                leg_price = leg.get("price")
                if isinstance(leg_price, dict) and leg_price.get("amount") is not None:
                    q[leg_key] = {**leg, "price": {**leg_price, "amount": float(leg_price["amount"]) * person_count}}
        scaled.append(q)
    return scaled
