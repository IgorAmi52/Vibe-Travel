from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from core.clients.base import IntentInferenceClient
from core.state import IntentStruct


@dataclass
class SyntheticIntentClient(IntentInferenceClient):
    intent_override: Optional[IntentStruct] = None

    def extract_intent(self, prompt: str, user_query: str) -> IntentStruct:
        del prompt
        if self.intent_override is not None:
            return self.intent_override.normalized()
        return _build_synthetic_intent(user_query)


def _build_synthetic_intent(user_query: str) -> IntentStruct:
    query = user_query.lower()
    budget = _extract_budget(user_query)
    start_date, end_date = _extract_iso_dates(user_query)

    if "alps" in query or "ski" in query or "snow" in query:
        return IntentStruct(
            places=["Chamonix", "Zermatt"],
            countries=["France", "Switzerland"],
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            vibe=["active", "ski resort", "mountain hotel"],
        )

    if "spain" in query or "beach" in query or "sea" in query:
        return IntentStruct(
            places=["Mallorca", "San Sebastian"],
            countries=["Spain", "Spain"],
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            vibe=["beach", "walkable", "boutique hotel"],
        )

    return IntentStruct(
        places=["Ljubljana", "Lake Bled"],
        countries=["Slovenia", "Slovenia"],
        start_date=start_date,
        end_date=end_date,
        budget=budget,
        vibe=["balanced", "scenic", "comfortable stay"],
    )


def _extract_budget(user_query: str) -> Optional[int]:
    scrubbed = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", user_query)
    currency_match = re.search(r"(?:\$|€|eur|usd)?\s*(\d{3,5})\b", scrubbed, flags=re.IGNORECASE)
    return int(currency_match.group(1)) if currency_match else None


def _extract_iso_dates(user_query: str) -> tuple[Optional[str], Optional[str]]:
    matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", user_query)
    if len(matches) >= 2:
        return matches[0], matches[1]
    if len(matches) == 1:
        return matches[0], None
    return None, None
