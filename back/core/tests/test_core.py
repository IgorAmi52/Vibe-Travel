import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.api import handle_invoke_request
from core.app import create_app
from core.clients.gemini import GeminiIntentClient
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
