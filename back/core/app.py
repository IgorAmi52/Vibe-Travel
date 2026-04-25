from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from clients import GeminiIntentClient, SyntheticIntentClient
from core.clients.base import IntentInferenceClient
from core.config import AppConfig, load_app_config, load_markdown_prompt
from core.graph import NodeHandler, TripPlannerGraphBuilder
from core.nodes import ExtractIntentNode
from core.state import IntentStruct, TripPlannerGraphState, create_initial_state


@dataclass
class TripPlannerApp:
    config: AppConfig
    _graph_parts: List[Tuple[str, NodeHandler]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.append_graph_part("extract_intent", self._create_extract_intent_node)

    def append_graph_part(self, name: str, handler: NodeHandler) -> None:
        self._graph_parts.append((name, handler))

    def run(
        self,
        user_query: str,
        mode: Optional[str] = None,
        source: str = "network",
        state: Optional[TripPlannerGraphState] = None,
        mock_response: Optional[Dict[str, Any]] = None,
    ) -> TripPlannerGraphState:
        selected_mode = (mode or self.config.default_mode).strip().lower()
        inference_client = self._create_inference_client(selected_mode, mock_response)
        graph = self._build_graph(inference_client)

        initial_state = dict(state or create_initial_state(user_query=user_query, source=source))
        initial_state["user_query"] = user_query
        initial_state.setdefault("source", source)
        initial_state["iteration"] = int(initial_state.get("iteration", 0)) + 1
        initial_state["needs_clarification"] = False
        initial_state["clarification_prompt"] = None
        return graph.invoke(initial_state)

    def _build_graph(self, inference_client: IntentInferenceClient) -> TripPlannerGraphBuilder:
        builder = TripPlannerGraphBuilder()
        prompt_loader = lambda: load_markdown_prompt(self.config.prompt_path)

        for name, handler in self._graph_parts:
            if name == "extract_intent":
                builder.append_part(name, ExtractIntentNode(inference_client, prompt_loader))
                continue
            builder.append_part(name, handler)

        return builder

    def _create_extract_intent_node(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        raise NotImplementedError("The extract-intent node is created dynamically per inference client.")

    def _create_inference_client(
        self,
        mode: str,
        mock_response: Optional[Dict[str, Any]],
    ) -> IntentInferenceClient:
        if mode == "gemini":
            return GeminiIntentClient(model=self.config.gemini_model)
        if mode == "mock":
            override = IntentStruct.from_dict(mock_response) if mock_response else None
            return SyntheticIntentClient(intent_override=override)
        raise ValueError(f"Unsupported mode '{mode}'. Expected 'mock' or 'gemini'.")


def create_app(config: Optional[AppConfig] = None) -> TripPlannerApp:
    return TripPlannerApp(config=config or load_app_config())
