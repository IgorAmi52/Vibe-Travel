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
        inferred_intent = self.inference_client.extract_intent(prompt=prompt, user_query=state["user_query"])
        merged_payload = inferred_intent.to_dict()
        explicit_trip_intent = state.get("trip_intent")
        if isinstance(explicit_trip_intent, dict):
            merged_payload.update(_clean_payload(explicit_trip_intent))
        trip_intent = IntentStruct.from_dict(merged_payload)
        return {
            "trip_intent": trip_intent.to_dict(),
            "status": "intent_ready",
            "next_step": "search_flights",
        }


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        cleaned[key] = value
    return cleaned
