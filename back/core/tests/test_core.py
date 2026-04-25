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
from core.graph import LANGGRAPH_AVAILABLE
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
        result = TripPlannerState.from_dict(
            app.run("I want an active Alps trip with skiing from 2026-12-20 to 2026-12-27 for 2400")
        )

        self.assertEqual(result.status, "intent_ready")
        self.assertEqual(result.next_step, "search_flights")
        self.assertEqual(result.trip_intent.places, ["Chamonix", "Zermatt"])
        self.assertEqual(result.trip_intent.countries, ["France", "Switzerland"])
        self.assertEqual(result.trip_intent.budget, 2400)
        self.assertFalse(result.needs_clarification)
        self.assertIsNone(result.clarification_prompt)
        self.assertEqual(result.iteration, 1)

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
                "mock_response": {
                    "places": ["Val d'Isere"],
                    "countries": ["France"],
                    "start_date": "2026-12-20",
                    "end_date": "2026-12-27",
                    "budget": 1800,
                    "vibe": ["ski in ski out", "spa"],
                },
            },
        )

        self.assertEqual(payload["state"]["trip_intent"]["places"], ["Val d'Isere"])
        self.assertEqual(payload["state"]["status"], "intent_ready")
        self.assertNotIn("needs_clarification", payload)

    def test_iteration_increments_across_turns(self) -> None:
        app = create_app(self.config)
        result1 = app.run("I want an Alps ski trip")
        self.assertEqual(result1["iteration"], 1)

        result2 = app.run("From 2026-12-20 to 2026-12-27", state=result1)
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

        result2 = app.run("Trip from 2026-12-20 to 2026-12-27", state=result1, mode="mock")
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
            app, {"type": "NEW", "user_query": "Alps ski trip", "mode": "mock"}
        )
        self.assertNotIn("needs_clarification", payload)
        self.assertIn("state", payload)

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
