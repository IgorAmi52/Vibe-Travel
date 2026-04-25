from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class IntentStruct:
    places: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[int] = None
    vibe: Optional[str] = None

    def normalized(self) -> "IntentStruct":
        return IntentStruct(
            places=_clean_string_list(self.places),
            countries=_clean_string_list(self.countries),
            start_date=_clean_optional_string(self.start_date),
            end_date=_clean_optional_string(self.end_date),
            budget=self.budget,
            vibe=self.vibe,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "IntentStruct":
        return cls(
            places=list(payload.get("places") or []),
            countries=list(payload.get("countries") or []),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            budget=payload.get("budget"),
            vibe=payload.get("vibe"),
        ).normalized()

    @staticmethod
    def json_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "places": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Travel places that match the user's requested vibe. "
                        "For example, if the user wants an active Alps trip, suggest ski resorts."
                    ),
                },
                "countries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Country names corresponding to places, aligned by index where possible.",
                },
                "start_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "description": "Trip start date in ISO-8601 format when provided or inferred, otherwise null.",
                },
                "end_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "description": "Trip end date in ISO-8601 format when provided or inferred, otherwise null.",
                },
                "budget": {
                    "type": ["integer", "null"],
                    "description": "Budget amount as a whole number in the user's implied currency.",
                },
                "vibe": {
                    "type": ["string", "null"],
                    "description": (
                        "Accommodation and trip vibe descriptors, including what kind of accommodation "
                        "the user wants and what matters to them."
                    ),
                },
            },
            "required": ["places", "countries", "start_date", "end_date", "budget", "vibe"],
            "additionalProperties": False,
            "propertyOrdering": [
                "places",
                "countries",
                "start_date",
                "end_date",
                "budget",
                "vibe",
            ],
        }


@dataclass
class TripPlannerState:
    user_query: str
    source: str = "network"
    status: str = "received"
    trip_intent: Optional[IntentStruct] = None
    next_step: Optional[str] = "extract_intent"
    errors: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
    iteration: int = 0

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if self.trip_intent is not None:
            payload["trip_intent"] = self.trip_intent.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TripPlannerState":
        trip_intent = payload.get("trip_intent")
        return cls(
            user_query=payload["user_query"],
            source=payload.get("source", "network"),
            status=payload.get("status", "received"),
            trip_intent=IntentStruct.from_dict(trip_intent) if trip_intent else None,
            next_step=payload.get("next_step", "extract_intent"),
            errors=list(payload.get("errors") or []),
            needs_clarification=bool(payload.get("needs_clarification", False)),
            clarification_prompt=payload.get("clarification_prompt"),
            iteration=int(payload.get("iteration", 0)),
        )


def create_initial_state(user_query: str, source: str = "network") -> Dict[str, Any]:
    return TripPlannerState(user_query=user_query, source=source).to_dict()


class TripPlannerGraphState(TypedDict, total=False):
    user_query: str
    source: str
    status: str
    trip_intent: Dict[str, Any]
    next_step: Optional[str]
    errors: List[str]
    needs_clarification: bool
    clarification_prompt: Optional[str]
    iteration: int


def _clean_string_list(values: List[str]) -> List[str]:
    cleaned: List[str] = []
    for value in values:
        normalized = _clean_optional_string(value)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def _clean_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
