from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.state import TripPlannerGraphState


@dataclass
class GroupResultsNode:
    flight_limit: int = 3
    hotel_limit: int = 3
    option_limit: int = 9

    def __call__(self, state: TripPlannerGraphState) -> Dict[str, Any]:
        flights = list(state.get("flight_results") or [])
        hotels = list(state.get("hotel_results") or [])
        if not flights or not hotels:
            return {
                "grouped_results": [],
                "status": state.get("status", "received"),
                "next_step": state.get("next_step"),
            }

        destination_place = state.get("destination_place")
        destination_iata = state.get("destination_iata")
        budget = _extract_budget(state)
        grouped_results: List[Dict[str, Any]] = []
        option_index = 1
        for flight in flights[: self.flight_limit]:
            for hotel in hotels[: self.hotel_limit]:
                total_amount = _sum_prices(
                    _extract_price_amount(flight.get("price")),
                    _extract_price_amount(hotel.get("price")),
                )
                within_budget = budget is None or (
                    total_amount is not None and total_amount <= float(budget)
                )
                grouped_results.append(
                    {
                        "option_id": f"option_{option_index}",
                        "destination": {
                            "place": destination_place,
                            "iata": destination_iata,
                        },
                        "flight": flight,
                        "hotel": hotel,
                        "within_budget": within_budget,
                        "price_summary": {
                            "flight_amount": _extract_price_amount(flight.get("price")),
                            "hotel_amount": _extract_price_amount(hotel.get("price")),
                            "total_amount": total_amount,
                            "currency": _extract_currency(flight.get("price"))
                            or _extract_currency(hotel.get("price")),
                            "budget": float(budget) if budget is not None else None,
                        },
                    }
                )
                option_index += 1

        grouped_results.sort(
            key=lambda item: (
                item["price_summary"]["total_amount"]
                if item["price_summary"]["total_amount"] is not None
                else float("inf"),
                -float(item["hotel"].get("scores", {}).get("composite_score") or 0.0),
            )
        )

        if budget is not None:
            grouped_results = [item for item in grouped_results if item.get("within_budget")]
            if not grouped_results:
                return {
                    "flight_results": [],
                    "hotel_results": [],
                    "grouped_results": [],
                    "status": "needs_clarification",
                    "next_step": "group_results",
                    "needs_clarification": True,
                    "clarification_prompt": (
                        f"I couldn't find any flight and hotel combinations within your budget of {budget}."
                    ),
                }

        return {
            "flight_results": [],
            "hotel_results": [],
            "grouped_results": grouped_results[: self.option_limit],
            "status": "travel_options_ready",
            "next_step": None,
        }


def _extract_price_amount(price: Any) -> float | None:
    if not isinstance(price, dict):
        return None
    value = price.get("amount")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_currency(price: Any) -> str | None:
    if not isinstance(price, dict):
        return None
    currency = price.get("currency") or price.get("unit")
    return str(currency) if currency else None


def _sum_prices(left: float | None, right: float | None) -> float | None:
    if left is None and right is None:
        return None
    return float(left or 0.0) + float(right or 0.0)


def _extract_budget(state: TripPlannerGraphState) -> int | None:
    budget = state.get("budget")
    if budget is None:
        trip_intent = state.get("trip_intent")
        if isinstance(trip_intent, dict):
            budget = trip_intent.get("budget")
    if budget is None:
        return None
    try:
        return int(budget)
    except (TypeError, ValueError):
        return None
