from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from core.clients.base import IntentInferenceClient
from core.state import IntentStruct
from core.state import TripPlannerGraphState


@dataclass
class ExtractIntentNode:
    inference_client: IntentInferenceClient
    prompt_loader: Callable[[], str]

    def __call__(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        prompt = self.prompt_loader()
        previous_intent = state.get("trip_intent") if isinstance(state.get("trip_intent"), dict) else {}
        contextual_query = _build_contextual_query(state["user_query"], previous_intent)
        inferred_intent = self.inference_client.extract_intent(prompt=prompt, user_query=contextual_query)
        merged_payload = _clean_payload(previous_intent or {})
        merged_payload.update(_clean_payload(inferred_intent.to_dict()))
        trip_intent = IntentStruct.from_dict(merged_payload)
        previous_places = list((previous_intent or {}).get("places") or [])
        new_places = list(trip_intent.to_dict().get("places") or [])
        result: Dict[str, Any] = {
            "trip_intent": trip_intent.to_dict(),
            "budget": trip_intent.budget,
            "status": "intent_ready",
            "next_step": "search_flights",
        }
        if trip_intent.person_count is not None:
            result["person_count"] = trip_intent.person_count
        # When the user's destination places change (e.g. via a clarification),
        # invalidate the previously resolved IATA/place so search_flights re-resolves
        # them against the new intent instead of reusing the stale destination.
        if previous_places != new_places:
            result["destination_iata"] = None
            result["destination_place"] = None
        return result


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        cleaned[key] = value
    return cleaned


def _build_contextual_query(user_query: str, previous_intent: Dict[str, Any]) -> str:
    """Wrap a clarification query with prior intent so the LLM has full context."""
    if not previous_intent:
        return user_query

    context_parts: list[str] = []
    if previous_intent.get("places"):
        context_parts.append(f"current places: {', '.join(previous_intent['places'])}")
    if previous_intent.get("countries"):
        context_parts.append(f"current countries: {', '.join(previous_intent['countries'])}")
    if previous_intent.get("start_date") and previous_intent.get("end_date"):
        context_parts.append(
            f"current dates: {previous_intent['start_date']} to {previous_intent['end_date']}"
        )
    if previous_intent.get("budget"):
        context_parts.append(f"current budget: {previous_intent['budget']}")
    if previous_intent.get("vibe"):
        context_parts.append(f"current vibe: {previous_intent['vibe']}")
    if previous_intent.get("person_count"):
        context_parts.append(f"current travellers: {previous_intent['person_count']}")

    if not context_parts:
        return user_query

    return (
        "Previous trip intent — " + "; ".join(context_parts) + ".\n"
        f"User refinement: {user_query}\n"
        "Re-extract the full intent. The user's refinement should override the "
        "matching previous fields; keep previous fields the user did not change."
    )
