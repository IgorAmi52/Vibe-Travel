from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.clients.base import IntentInferenceClient
from core.state import TripPlannerGraphState


@dataclass
class ExtractIntentNode:
    inference_client: IntentInferenceClient
    prompt_loader: Callable[[], str]

    def __call__(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        prompt = self.prompt_loader()
        trip_intent = self.inference_client.extract_intent(prompt=prompt, user_query=state["user_query"])
        return {
            "trip_intent": trip_intent.to_dict(),
            "status": "intent_ready",
            "next_step": "search_flights",
        }
