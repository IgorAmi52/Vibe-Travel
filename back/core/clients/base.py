from __future__ import annotations

from abc import ABC, abstractmethod

from core.state import IntentStruct


class IntentInferenceClient(ABC):
    @abstractmethod
    def extract_intent(self, prompt: str, user_query: str) -> IntentStruct:
        raise NotImplementedError
