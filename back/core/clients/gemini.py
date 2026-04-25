from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

from core.clients.base import IntentInferenceClient
from core.config import load_env_file
from core.state import IntentStruct


class GeminiIntentClient(IntentInferenceClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash-lite",
    ) -> None:
        load_env_file()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model

    def extract_intent(self, prompt: str, user_query: str) -> IntentStruct:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required to call Gemini intent inference.")

        client, sdk_types = self._load_sdk()
        response = client.models.generate_content(
            model=self.model,
            contents=self._build_contents(prompt=prompt, user_query=user_query),
            config=sdk_types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=IntentStruct.json_schema(),
            ),
        )
        return IntentStruct.from_dict(self._extract_json_payload(response))

    def _load_sdk(self) -> Tuple[Any, Any]:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError(
                "The new Gemini SDK is required. Install it with: pip install -U google-genai"
            ) from exc

        client_kwargs: Dict[str, Any] = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        return genai.Client(**client_kwargs), types

    @staticmethod
    def _build_contents(prompt: str, user_query: str) -> str:
        return (
            f"{prompt}\n\n"
            "Return only a JSON object that matches the schema.\n"
            f"User request: {user_query}"
        )

    @staticmethod
    def _extract_json_payload(response: Any) -> Dict[str, Any]:
        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini response did not contain a JSON text payload.")

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini response was not valid JSON: {text}") from exc
