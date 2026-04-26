from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from clients import GeminiIntentClient, SyntheticIntentClient
from clients.api_connector import ApiConnector
from clients.booking_client import BookingComClient
from clients.cosine_similarity_service import CosineSimilarityService
from clients.gemini_embed_provider import GeminiEmbedProvider
from core.clients import SkyscannerFlightClient
from core.clients.mock_flights import SyntheticFlightClient
from core.clients.base import IntentInferenceClient
from core.config import AppConfig, load_app_config, load_markdown_prompt
from core.flights import FlightChainService
from core.graph import NodeHandler, TripPlannerGraphBuilder
from core.nodes import ExtractIntentNode, GroupResultsNode, SearchFlightsNode, SearchHotelsNode
from core.services.hotel_embedding_service_impl import HotelEmbeddingServiceImpl
from core.services.hotel_ranking_service import HotelRankingService
from core.state import IntentStruct, TripPlannerGraphState, create_initial_state


@dataclass
class TripPlannerApp:
    config: AppConfig
    _graph_parts: List[Tuple[str, NodeHandler]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.append_graph_part("extract_intent", self._create_extract_intent_node)
        self.append_graph_part("search_flights", self._create_search_flights_node)
        self.append_graph_part("search_hotels", self._create_search_hotels_node)
        self.append_graph_part("group_results", self._create_group_results_node)

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
        flight_service = self._create_flight_service(selected_mode)
        graph = self._build_graph(inference_client, flight_service)

        initial_state = dict(state or create_initial_state(user_query=user_query, source=source))
        initial_state["user_query"] = user_query
        initial_state.setdefault("source", source)
        initial_state["iteration"] = int(initial_state.get("iteration", 0)) + 1
        initial_state["needs_clarification"] = False
        initial_state["clarification_prompt"] = None
        return graph.invoke(initial_state)

    def _build_graph(
        self,
        inference_client: IntentInferenceClient,
        flight_service: FlightChainService,
    ) -> TripPlannerGraphBuilder:
        builder = TripPlannerGraphBuilder()
        prompt_loader = lambda: load_markdown_prompt(self.config.prompt_path)

        for name, handler in self._graph_parts:
            if name == "extract_intent":
                builder.append_part(name, ExtractIntentNode(inference_client, prompt_loader))
                continue
            if name == "search_flights":
                builder.append_part(name, SearchFlightsNode(flight_service=flight_service))
                continue
            if name == "search_hotels":
                builder.append_part(name, SearchHotelsNode(hotel_ranking_service_factory=self._create_hotel_ranking_service))
                continue
            if name == "group_results":
                builder.append_part(name, GroupResultsNode())
                continue
            builder.append_part(name, handler)

        return builder

    def _create_extract_intent_node(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        raise NotImplementedError("The extract-intent node is created dynamically per inference client.")

    def _create_search_flights_node(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        raise NotImplementedError("The search-flights node is created dynamically per flight service.")

    def _create_search_hotels_node(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        raise NotImplementedError("The search-hotels node is created dynamically per hotel ranking service.")

    def _create_group_results_node(self, state: TripPlannerGraphState) -> TripPlannerGraphState:
        raise NotImplementedError("The group-results node is created dynamically.")

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

    def _create_flight_service(self, mode: str) -> FlightChainService:
        if mode == "mock":
            return FlightChainService(provider=SyntheticFlightClient())

        return FlightChainService(
            provider=SkyscannerFlightClient(
                base_url=self.config.skyscanner_base_url,
                api_key=self.config.skyscanner_api_key,
                api_host=self.config.skyscanner_api_host,
                timeout=self.config.skyscanner_timeout_seconds,
                max_retries=self.config.skyscanner_max_retries,
                retry_delay=self.config.skyscanner_retry_delay_seconds,
            )
        )

    def _create_hotel_ranking_service(self) -> HotelRankingService:
        if not self.config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for hotel ranking.")
        connector = ApiConnector(
            base_url=self.config.booking_base_url,
            headers={
                "X-RapidAPI-Key": self.config.booking_api_key,
                "X-RapidAPI-Host": self.config.booking_api_host,
            },
            timeout=self.config.booking_timeout_seconds,
            max_retries=self.config.booking_max_retries,
            retry_delay=self.config.booking_retry_delay_seconds,
        )
        return HotelRankingService(
            hotel_api=BookingComClient(api_connector=connector),
            embedding_service=HotelEmbeddingServiceImpl(
                GeminiEmbedProvider(
                    api_key=self.config.gemini_api_key,
                    model=self.config.gemini_embedding_model,
                )
            ),
            similarity_service=CosineSimilarityService(),
            vibe_weight=self.config.hotel_vibe_weight,
            price_weight=self.config.hotel_price_weight,
            rating_weight=self.config.hotel_rating_weight,
        )


def create_app(config: Optional[AppConfig] = None) -> TripPlannerApp:
    return TripPlannerApp(config=config or load_app_config())
