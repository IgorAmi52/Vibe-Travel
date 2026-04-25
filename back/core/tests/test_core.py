import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.api import handle_flight_chain_request, handle_flight_indicative_request, handle_invoke_request
from core.app import create_app
from clients.gemini import GeminiIntentClient
from core.config import DEFAULT_PROMPT_PATH, AppConfig, load_app_config, load_env_file, load_markdown_prompt
from core.flights import (
    FlightChainService,
    FlightLegChain,
    FlightSegment,
    LivePricesPollResult,
    RoundTripChainResult,
)
from core.graph import LANGGRAPH_AVAILABLE
from core.nodes.group_results import GroupResultsNode
from core.nodes.search_flights import SearchFlightsNode
from core.nodes.search_hotels import SearchHotelsNode
from core.models.hotel import Hotel, ScoredHotel
from core.state import TripPlannerState, create_initial_state


class CoreModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = AppConfig(
            prompt_path=DEFAULT_PROMPT_PATH,
            default_mode="mock",
            api_host="127.0.0.1",
            api_port=0,
            gemini_model="gemini-2.5-flash-lite",
        )
        self.langgraph_patch = patch(
            "core.graph.planner.load_langgraph_components",
            return_value=_fake_langgraph_components(),
        )
        self.langgraph_patch.start()

    def tearDown(self) -> None:
        self.langgraph_patch.stop()

    def test_create_initial_state(self) -> None:
        state = TripPlannerState.from_dict(create_initial_state("Need a ski trip"))
        self.assertEqual(state.user_query, "Need a ski trip")
        self.assertEqual(state.source, "network")
        self.assertEqual(state.status, "received")
        self.assertEqual(state.next_step, "extract_intent")
        self.assertEqual(state.errors, [])
        self.assertIsNone(state.trip_intent)
        self.assertFalse(state.needs_clarification)
        self.assertIsNone(state.clarification_prompt)
        self.assertEqual(state.iteration, 0)

    def test_prompt_loader_reads_markdown_prompt(self) -> None:
        prompt = load_markdown_prompt(DEFAULT_PROMPT_PATH)
        self.assertIn("structured travel intent", prompt)
        self.assertIn("Return only valid JSON.", prompt)

    def test_env_file_populates_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "GEMINI_API_KEY=test-key-from-env\nTRIP_PLANNER_MODE=gemini\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                load_env_file(env_path)
                config = load_app_config()
                self.assertEqual(os.environ["GEMINI_API_KEY"], "test-key-from-env")
                self.assertEqual(config.default_mode, "gemini")

    def test_app_invocation_uses_mock_mode_by_default(self) -> None:
        app = create_app(self.config)
        result = app.run(
            "I want an active Alps trip with skiing for 2400",
            state={"origin_iata": "VIE", "destination_iata": "CMF"},
        )

        self.assertEqual(result["status"], "indicative_flights_ready")
        self.assertEqual(result["next_step"], "select_dates")
        self.assertEqual(result["trip_intent"]["places"], ["Chamonix", "Zermatt"])
        self.assertEqual(result["trip_intent"]["countries"], ["France", "Switzerland"])
        self.assertEqual(result["trip_intent"]["budget"], 2400)
        self.assertFalse(result["needs_clarification"])
        self.assertIsNone(result["clarification_prompt"])
        self.assertEqual(result["iteration"], 1)
        self.assertGreater(len(result["flight_results"]), 0)
        self.assertEqual(result["hotel_results"], [])
        self.assertEqual(result["grouped_results"], [])

    def test_app_can_append_more_graph_parts(self) -> None:
        app = create_app(self.config)

        def tag_geo_ready(state):
            self.assertIn("trip_intent", state)
            return {"status": "geo_ready", "next_step": "search_hotels"}

        app.append_graph_part("prepare_geo_filters", tag_geo_ready)
        result = app.run("Find me a luxury beach break in Spain")

        self.assertEqual(result["status"], "geo_ready")
        self.assertEqual(result["next_step"], "search_hotels")

    def test_langgraph_availability_flag_is_boolean(self) -> None:
        self.assertIsInstance(LANGGRAPH_AVAILABLE, bool)

    def test_gemini_client_uses_new_sdk_config_and_schema(self) -> None:
        captured = {}

        class FakeModels:
            def generate_content(self, *, model, contents, config):
                captured["model"] = model
                captured["contents"] = contents
                captured["config"] = config
                return type(
                    "FakeResponse",
                    (),
                    {
                        "text": (
                            '{"places":["Chamonix"],"countries":["France"],'
                            '"start_date":"2026-12-20","end_date":"2026-12-27",'
                            '"budget":2000,"vibe":["skiing","spa hotel"]}'
                        )
                    },
                )()

        class FakeClient:
            def __init__(self):
                self.models = FakeModels()

        class FakeTypes:
            @staticmethod
            def GenerateContentConfig(**kwargs):
                return kwargs

        client = GeminiIntentClient(api_key="test-key")
        client._load_sdk = lambda: (FakeClient(), FakeTypes)  # type: ignore[method-assign]

        result = client.extract_intent(
            prompt="Extract intent in JSON.",
            user_query="I want an active Alps trip with skiing and a spa hotel.",
        )

        self.assertEqual(result.places, ["Chamonix"])
        self.assertEqual(result.countries, ["France"])
        self.assertEqual(captured["model"], "gemini-2.5-flash-lite")
        self.assertEqual(captured["config"]["response_mime_type"], "application/json")
        self.assertEqual(
            captured["config"]["response_json_schema"]["required"],
            ["places", "countries", "start_date", "end_date", "budget", "vibe"],
        )
        self.assertIn("User request:", captured["contents"])

    def test_api_payload_handler_supports_mock_invocation(self) -> None:
        app = create_app(self.config)
        payload = handle_invoke_request(
            app,
            {
                "type": "NEW",
                "user_query": "Plan an Alps ski trip",
                "mode": "mock",
                "origin_iata": "VIE",
                "destination_iata": "LYS",
                "mock_response": {
                    "places": ["Val d'Isere"],
                    "countries": ["France"],
                    "start_date": None,
                    "end_date": None,
                    "budget": 1800,
                    "vibe": ["ski in ski out", "spa"],
                },
            },
        )

        self.assertEqual(payload["state"]["trip_intent"]["places"], ["Val d'Isere"])
        self.assertEqual(payload["state"]["status"], "indicative_flights_ready")
        self.assertEqual(payload["state"]["next_step"], "select_dates")
        self.assertGreater(len(payload["state"]["flight_results"]), 0)
        self.assertEqual(payload["state"]["hotel_results"], [])
        self.assertEqual(payload["state"]["grouped_results"], [])
        self.assertNotIn("needs_clarification", payload)

    def test_iteration_increments_across_turns(self) -> None:
        app = create_app(self.config)
        result1 = app.run("I want an Alps ski trip")
        self.assertEqual(result1["iteration"], 1)

        result2 = app.run("From Vienna please", state=result1)
        self.assertEqual(result2["iteration"], 2)

    def test_clarification_node_signals_are_surfaced(self) -> None:
        app = create_app(self.config)

        def always_needs_clarification(state):
            return {
                "needs_clarification": True,
                "clarification_prompt": "What are your travel dates?",
                "status": "needs_clarification",
            }

        app.append_graph_part("check_completeness", always_needs_clarification)
        payload = handle_invoke_request(
            app,
            {"type": "NEW", "user_query": "I want a trip somewhere nice", "mode": "mock"},
        )

        self.assertTrue(payload["needs_clarification"])
        self.assertEqual(payload["clarification_prompt"], "What are your travel dates?")
        self.assertTrue(payload["state"]["needs_clarification"])

    def test_clarification_resets_on_each_run(self) -> None:
        app = create_app(self.config)
        call_count = {"n": 0}

        def sometimes_needs_clarification(state):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"needs_clarification": True, "clarification_prompt": "Dates?"}
            return {"needs_clarification": False, "clarification_prompt": None}

        app.append_graph_part("check_completeness", sometimes_needs_clarification)

        result1 = app.run("Trip somewhere", mode="mock")
        self.assertTrue(result1["needs_clarification"])

        result2 = app.run("Trip with a bit more detail", state=result1, mode="mock")
        self.assertFalse(result2["needs_clarification"])
        self.assertIsNone(result2["clarification_prompt"])
        self.assertEqual(result2["iteration"], 2)

    def test_clarification_type_carries_prior_state(self) -> None:
        app = create_app(self.config)
        result1 = handle_invoke_request(
            app, {"type": "NEW", "user_query": "Alps ski trip", "mode": "mock"}
        )
        result2 = handle_invoke_request(
            app,
            {
                "type": "CLARIFICATION",
                "user_query": "Alps ski trip, Dec 20–27, budget 2500",
                "mode": "mock",
                "state": result1["state"],
            },
        )
        self.assertEqual(result2["state"]["iteration"], 2)

    def test_new_type_ignores_prior_state(self) -> None:
        app = create_app(self.config)
        result1 = handle_invoke_request(
            app, {"type": "NEW", "user_query": "Alps ski trip", "mode": "mock"}
        )
        result2 = handle_invoke_request(
            app,
            {
                "type": "NEW",
                "user_query": "Beach trip to Spain",
                "mode": "mock",
                "state": result1["state"],
            },
        )
        self.assertEqual(result2["state"]["iteration"], 1)

    def test_invalid_type_raises_value_error(self) -> None:
        app = create_app(self.config)
        with self.assertRaises(ValueError):
            handle_invoke_request(
                app, {"type": "RETRY", "user_query": "Alps ski trip", "mode": "mock"}
            )

    def test_needs_clarification_absent_from_normal_api_response(self) -> None:
        app = create_app(self.config)
        payload = handle_invoke_request(
            app,
            {
                "type": "NEW",
                "user_query": "Alps ski trip",
                "mode": "mock",
                "origin_iata": "VIE",
                "destination_iata": "CMF",
            },
        )
        self.assertNotIn("needs_clarification", payload)
        self.assertIn("state", payload)
        self.assertEqual(payload["state"]["status"], "indicative_flights_ready")
        self.assertEqual(payload["state"]["hotel_results"], [])
        self.assertEqual(payload["state"]["grouped_results"], [])

    def test_flight_chain_rejects_return_before_departure(self) -> None:
        app = create_app(self.config)

        with self.assertRaisesRegex(ValueError, "return_date must be on or after departure_date"):
            handle_flight_chain_request(
                app,
                {
                    "origin_iata": "VIE",
                    "destination_iata": "LON",
                    "departure_date": "2026-06-20",
                    "return_date": "2026-06-10",
                },
            )

    def test_config_clamps_skyscanner_max_retries_to_minimum_one(self) -> None:
        with patch.dict(os.environ, {"SKYSCANNER_MAX_RETRIES": "0"}, clear=True):
            config = load_app_config()
            self.assertEqual(config.skyscanner_max_retries, 1)

    def test_flight_indicative_requires_valid_outbound_date(self) -> None:
        app = create_app(self.config)

        with self.assertRaisesRegex(ValueError, "outbound_date must be ISO format YYYY-MM-DD"):
            handle_flight_indicative_request(
                app,
                {
                    "origin_iata": "VIE",
                    "outbound_date": "07-01-2026",
                },
            )

    def test_search_flights_uses_indicative_anywhere_without_destination(self) -> None:
        class _Provider:
            def __init__(self) -> None:
                self.closed = False

            async def search_roundtrip_chains(self, params):
                raise AssertionError("roundtrip search should not run when destination_iata is missing")

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata=None,
                outbound_date=None,
                return_date=None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                del return_date
                return {
                    "status": "RESULT_STATUS_COMPLETE",
                    "quotes": [
                        {
                            "airports": {
                                "origin": {"iata": origin_iata, "name": origin_iata},
                                "destination": {"iata": "AGP", "name": "Malaga"},
                            },
                            "outbound_datetime": (
                                f"{outbound_date}T00:00:00" if outbound_date else None
                            ),
                            "inbound_datetime": None,
                            "price": {"amount": 89.0, "unit": "PRICE_UNIT_WHOLE"},
                        }
                    ],
                }

            async def close(self) -> None:
                self.closed = True

        provider = _Provider()
        node = SearchFlightsNode(flight_service=FlightChainService(provider=provider))
        result = node(
            {
                "origin_iata": "VIE",
                "trip_intent": {"start_date": "2026-07-01"},
            }
        )

        self.assertEqual(result["status"], "indicative_flights_ready")
        self.assertEqual(result["next_step"], "select_destination")
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(result["flight_results"][0]["airports"]["destination"]["iata"], "AGP")
        self.assertTrue(provider.closed)

    def test_search_flights_uses_anytime_indicative_without_destination_and_dates(self) -> None:
        class _Provider:
            def __init__(self) -> None:
                self.closed = False

            async def search_roundtrip_chains(self, params):
                raise AssertionError("roundtrip search should not run when destination_iata is missing")

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata=None,
                outbound_date=None,
                return_date=None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                del return_date
                return {
                    "status": "RESULT_STATUS_COMPLETE",
                    "quotes": [
                        {
                            "airports": {
                                "origin": {"iata": origin_iata, "name": origin_iata},
                                "destination": {"iata": "PMI", "name": "Palma"},
                            },
                            "outbound_datetime": (
                                f"{outbound_date}T00:00:00" if outbound_date else None
                            ),
                            "inbound_datetime": None,
                            "price": {"amount": 120.0, "unit": "PRICE_UNIT_WHOLE"},
                        }
                    ],
                }

            async def close(self) -> None:
                self.closed = True

        provider = _Provider()
        node = SearchFlightsNode(flight_service=FlightChainService(provider=provider))
        result = node({"origin_iata": "VIE", "trip_intent": {}})

        self.assertEqual(result["status"], "indicative_flights_ready")
        self.assertEqual(result["next_step"], "select_destination")
        self.assertFalse(result["needs_clarification"])
        self.assertEqual(result["flight_results"][0]["airports"]["destination"]["iata"], "PMI")
        self.assertTrue(provider.closed)

    def test_search_flights_resolves_destination_from_places_and_defaults_origin_to_bcn(self) -> None:
        class _Provider:
            def __init__(self) -> None:
                self.closed = False
                self.calls = []

            async def resolve_iata_code(self, search_term: str, *, market: str = "UK", locale: str = "en-GB"):
                del market, locale
                if search_term == "Paris":
                    return "CDG"
                return None

            async def search_roundtrip_chains(self, params):
                raise AssertionError("roundtrip search should not run in indicative date-range flow")

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata=None,
                outbound_date=None,
                return_date=None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                self.calls.append(
                    {
                        "origin_iata": origin_iata,
                        "destination_iata": destination_iata,
                        "outbound_date": outbound_date,
                        "return_date": return_date,
                        "market": market,
                        "locale": locale,
                        "currency": currency,
                    }
                )
                if origin_iata == "BCN":
                    return {
                        "status": "RESULT_STATUS_COMPLETE",
                        "quotes": [
                            {
                                "airports": {
                                    "origin": {"iata": "BCN", "name": "Barcelona"},
                                    "destination": {"iata": "CDG", "name": "Paris"},
                                },
                                "outbound_datetime": "2026-07-01T09:00:00",
                                "price": {"amount": 70.0, "unit": "PRICE_UNIT_WHOLE"},
                                "carrier": {"name": "Outbound"},
                                "is_direct": True,
                            }
                        ],
                    }
                return {
                    "status": "RESULT_STATUS_COMPLETE",
                    "quotes": [
                        {
                            "airports": {
                                "origin": {"iata": "CDG", "name": "Paris"},
                                "destination": {"iata": "BCN", "name": "Barcelona"},
                            },
                            "outbound_datetime": "2026-07-05T18:00:00",
                            "price": {"amount": 80.0, "unit": "PRICE_UNIT_WHOLE"},
                            "carrier": {"name": "Inbound"},
                            "is_direct": True,
                        }
                    ],
                }

            async def close(self) -> None:
                self.closed = True

        provider = _Provider()
        node = SearchFlightsNode(flight_service=FlightChainService(provider=provider))
        result = node(
            {
                "trip_intent": {
                    "places": ["Paris"],
                    "start_date": "2026-07-01",
                    "end_date": "2026-07-05",
                }
            }
        )

        self.assertEqual(result["status"], "flights_ready")
        self.assertEqual(result["origin_iata"], "BCN")
        self.assertEqual(result["destination_place"], "Paris")
        self.assertEqual(result["destination_iata"], "CDG")
        self.assertEqual(result["next_step"], "search_hotels")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.calls[0]["origin_iata"], "BCN")
        self.assertEqual(provider.calls[0]["destination_iata"], "CDG")
        self.assertEqual(provider.calls[0]["outbound_date"], "2026-07-01")
        self.assertEqual(provider.calls[0]["return_date"], None)
        self.assertEqual(provider.calls[1]["origin_iata"], "CDG")
        self.assertEqual(provider.calls[1]["destination_iata"], "BCN")
        self.assertEqual(provider.calls[1]["outbound_date"], "2026-07-05")
        self.assertEqual(provider.calls[1]["return_date"], None)
        self.assertEqual(result["flight_results"][0]["outbound_datetime"], "2026-07-01T09:00:00")
        self.assertEqual(result["flight_results"][0]["inbound_datetime"], "2026-07-05T18:00:00")
        self.assertEqual(result["flight_results"][0]["price"]["amount"], 150.0)
        self.assertTrue(provider.closed)

    def test_search_flights_uses_indicative_with_destination_when_dates_missing(self) -> None:
        class _Provider:
            def __init__(self) -> None:
                self.closed = False
                self.calls = []

            async def resolve_iata_code(self, search_term: str, *, market: str = "UK", locale: str = "en-GB"):
                del market, locale
                if search_term == "Paris":
                    return "CDG"
                return search_term

            async def search_roundtrip_chains(self, params):
                raise AssertionError("roundtrip search should not run when dates are missing")

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata=None,
                outbound_date=None,
                return_date=None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                self.calls.append(
                    {
                        "origin_iata": origin_iata,
                        "destination_iata": destination_iata,
                        "outbound_date": outbound_date,
                        "return_date": return_date,
                        "market": market,
                        "locale": locale,
                        "currency": currency,
                    }
                )
                return {
                    "status": "RESULT_STATUS_COMPLETE",
                    "quotes": [
                        {
                            "airports": {
                                "origin": {"iata": origin_iata, "name": origin_iata},
                                "destination": {"iata": destination_iata, "name": destination_iata},
                            },
                            "outbound_datetime": (
                                f"{outbound_date}T00:00:00" if outbound_date else None
                            ),
                            "inbound_datetime": None,
                            "price": {"amount": 89.0, "unit": "PRICE_UNIT_WHOLE"},
                        }
                    ],
                }

            async def close(self) -> None:
                self.closed = True

        provider = _Provider()
        node = SearchFlightsNode(flight_service=FlightChainService(provider=provider))
        result = node({"trip_intent": {"places": ["Paris"]}})

        self.assertEqual(result["status"], "indicative_flights_ready")
        self.assertEqual(result["origin_iata"], "BCN")
        self.assertEqual(result["destination_place"], "Paris")
        self.assertEqual(result["destination_iata"], "CDG")
        self.assertEqual(result["next_step"], "select_dates")
        self.assertEqual(provider.calls[0]["destination_iata"], "CDG")
        self.assertIsNone(provider.calls[0]["outbound_date"])
        self.assertIsNone(provider.calls[0]["return_date"])
        self.assertTrue(provider.closed)

    def test_search_flights_tries_next_place_when_first_cannot_be_resolved(self) -> None:
        class _Provider:
            def __init__(self) -> None:
                self.closed = False
                self.calls = []

            async def resolve_iata_code(self, search_term: str, *, market: str = "UK", locale: str = "en-GB"):
                del market, locale
                if search_term == "Chamonix":
                    return None
                if search_term == "Zermatt":
                    return "ZRH"
                return None

            async def search_roundtrip_chains(self, params):
                raise AssertionError("roundtrip search should not run when dates are missing")

            async def search_indicative_anywhere(
                self,
                *,
                origin_iata: str,
                destination_iata=None,
                outbound_date=None,
                return_date=None,
                market: str = "UK",
                locale: str = "en-GB",
                currency: str = "EUR",
            ):
                self.calls.append(
                    {
                        "origin_iata": origin_iata,
                        "destination_iata": destination_iata,
                        "outbound_date": outbound_date,
                        "return_date": return_date,
                    }
                )
                return {
                    "status": "RESULT_STATUS_COMPLETE",
                    "quotes": [
                        {
                            "airports": {
                                "origin": {"iata": origin_iata, "name": origin_iata},
                                "destination": {"iata": destination_iata, "name": destination_iata},
                            },
                            "outbound_datetime": None,
                            "inbound_datetime": None,
                            "price": {"amount": 110.0, "unit": "PRICE_UNIT_WHOLE"},
                        }
                    ],
                }

            async def close(self) -> None:
                self.closed = True

        provider = _Provider()
        node = SearchFlightsNode(flight_service=FlightChainService(provider=provider))
        result = node({"trip_intent": {"places": ["Chamonix", "Zermatt", "Grindelwald"]}})

        self.assertEqual(result["status"], "indicative_flights_ready")
        self.assertEqual(result["destination_place"], "Zermatt")
        self.assertEqual(result["destination_iata"], "ZRH")
        self.assertEqual(result["next_step"], "select_dates")
        self.assertEqual(provider.calls[0]["destination_iata"], "ZRH")
        self.assertTrue(provider.closed)

    def test_search_hotels_falls_back_to_flight_dates_when_intent_dates_missing(self) -> None:
        class _HotelService:
            def __init__(self) -> None:
                self.calls = []
                self.closed = False

            async def rank_hotels(self, *, vibe_query, destination, check_in, check_out, currency="USD"):
                self.calls.append(
                    {
                        "vibe_query": vibe_query,
                        "destination": destination,
                        "check_in": check_in.isoformat(),
                        "check_out": check_out.isoformat(),
                        "currency": currency,
                    }
                )
                return [
                    ScoredHotel(
                        hotel=Hotel(
                            hotel_id="h-1",
                            name="Paris Spa Retreat",
                            price=320.0,
                            currency="USD",
                            description="Spa hotel",
                            amenities=["spa"],
                            guest_rating=9.1,
                        ),
                        vibe_similarity=0.9,
                        price_score=0.7,
                        guest_rating_score=0.91,
                        composite_score=0.85,
                    )
                ]

            async def close(self) -> None:
                self.closed = True

        hotel_service = _HotelService()
        node = SearchHotelsNode(hotel_ranking_service_factory=lambda: hotel_service)
        result = node(
            {
                "status": "flights_ready",
                "user_query": "Paris with a great spa",
                "destination_place": "Paris",
                "trip_intent": {
                    "places": ["Paris"],
                    "vibe": "spa center",
                },
                "flight_results": [
                    {
                        "outbound_datetime": "2026-08-10T09:00:00",
                        "inbound_datetime": "2026-08-14T18:00:00",
                    }
                ],
            }
        )

        self.assertEqual(result["status"], "hotels_ranked")
        self.assertEqual(result["next_step"], "group_results")
        self.assertEqual(hotel_service.calls[0]["check_in"], "2026-08-10")
        self.assertEqual(hotel_service.calls[0]["check_out"], "2026-08-14")
        self.assertEqual(result["hotel_results"][0]["name"], "Paris Spa Retreat")
        self.assertTrue(hotel_service.closed)

    def test_group_results_filters_final_offers_by_budget(self) -> None:
        node = GroupResultsNode(flight_limit=2, hotel_limit=2, option_limit=4)
        result = node(
            {
                "budget": 300,
                "destination_place": "Paris",
                "destination_iata": "CDG",
                "flight_results": [
                    {"price": {"amount": 120.0, "unit": "EUR"}},
                    {"price": {"amount": 220.0, "unit": "EUR"}},
                ],
                "hotel_results": [
                    {"name": "Budget Stay", "price": {"amount": 150.0, "currency": "EUR"}, "scores": {"composite_score": 0.7}},
                    {"name": "Luxury Stay", "price": {"amount": 260.0, "currency": "EUR"}, "scores": {"composite_score": 0.9}},
                ],
            }
        )

        self.assertEqual(result["status"], "travel_options_ready")
        self.assertEqual(len(result["grouped_results"]), 1)
        self.assertEqual(result["flight_results"], [])
        self.assertEqual(result["hotel_results"], [])
        self.assertEqual(result["grouped_results"][0]["hotel"]["name"], "Budget Stay")
        self.assertTrue(result["grouped_results"][0]["within_budget"])
        self.assertEqual(result["grouped_results"][0]["price_summary"]["total_amount"], 270.0)

    def test_group_results_returns_clarification_when_budget_cannot_be_met(self) -> None:
        node = GroupResultsNode()
        result = node(
            {
                "budget": 200,
                "flight_results": [{"price": {"amount": 180.0, "unit": "EUR"}}],
                "hotel_results": [{"name": "Hotel", "price": {"amount": 150.0, "currency": "EUR"}, "scores": {"composite_score": 0.8}}],
            }
        )

        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["next_step"], "group_results")
        self.assertTrue(result["needs_clarification"])
        self.assertEqual(result["flight_results"], [])
        self.assertEqual(result["hotel_results"], [])
        self.assertEqual(result["grouped_results"], [])

    @unittest.skipUnless(
        os.environ.get("BOOKING_RAPIDAPI_KEY") and os.environ.get("GEMINI_API_KEY"),
        "Real hotel ranking test requires BOOKING_RAPIDAPI_KEY and GEMINI_API_KEY",
    )
    def test_app_ranks_hotels_and_groups_results_after_full_flights(self) -> None:
        app = create_app(self.config)
        result = app.run(
            "Four days in paris, with awesome spa center, I am going with my mom and dad",
            state={
                "origin_iata": "BCN",
                "trip_intent": {
                    "places": ["Paris"],
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-14",
                    "vibe": "family-friendly, spa center",
                },
            },
        )

        self.assertEqual(result["status"], "travel_options_ready")
        self.assertEqual(result["destination_place"], "Paris")
        self.assertEqual(result["flight_results"], [])
        self.assertEqual(result["hotel_results"], [])
        self.assertGreater(len(result["grouped_results"]), 0)
        self.assertIn("hotel", result["grouped_results"][0])
        self.assertIn("flight", result["grouped_results"][0])

    def test_app_skips_hotel_ranking_until_dates_are_known(self) -> None:
        app = create_app(self.config)
        result = app.run(
            "Four days in paris, with awesome spa center",
            state={
                "origin_iata": "BCN",
                "trip_intent": {
                    "places": ["Paris"],
                    "vibe": "spa center",
                },
            },
        )

        self.assertEqual(result["status"], "indicative_flights_ready")
        self.assertEqual(result["next_step"], "select_dates")
        self.assertEqual(result["hotel_results"], [])
        self.assertEqual(result["grouped_results"], [])


if __name__ == "__main__":
    unittest.main()


def _fake_langgraph_components():
    class FakeCompiledGraph:
        def __init__(self, ordered_nodes):
            self._ordered_nodes = ordered_nodes

        def invoke(self, state):
            current_state = dict(state)
            for _, node in self._ordered_nodes:
                update = node(current_state)
                current_state.update(update)
            return current_state

    class FakeStateGraph:
        def __init__(self, _state_type):
            self._nodes = {}
            self._edges = {}

        def add_node(self, name, handler):
            self._nodes[name] = handler

        def add_edge(self, source, target):
            self._edges[source] = target

        def compile(self):
            ordered_nodes = []
            current = self._edges.get("__start__")
            while current and current != "__end__":
                ordered_nodes.append((current, self._nodes[current]))
                current = self._edges.get(current)
            return FakeCompiledGraph(ordered_nodes)

    class FakeComponents:
        START = "__start__"
        END = "__end__"
        StateGraph = FakeStateGraph

    return FakeComponents()
