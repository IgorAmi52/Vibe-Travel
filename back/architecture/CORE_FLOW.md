# Core Flow & Extension Points

## Overview

The backend is a LangGraph pipeline that takes a free-form travel query and produces a structured `IntentStruct`. It is split into two layers:

- **`core/`** — interfaces, state, graph assembly, and the HTTP API
- **`clients/`** — concrete inference backends (Gemini, mock) and HTTP connectors

---

## Structure

```
back/
├── main.py                        entry point — CLI and serve commands
├── clients/
│   ├── api_connector.py           async HTTP client with retry logic
│   ├── gemini.py                  GeminiIntentClient — calls Gemini structured output API
│   └── mock.py                    SyntheticIntentClient — rule-based, no network
└── core/
    ├── app.py                     TripPlannerApp — graph assembly and runtime
    ├── state.py                   IntentStruct, TripPlannerState, TripPlannerGraphState
    ├── api/
    │   ├── __init__.py            exposes: create_http_server, serve_http, handle_invoke_request
    │   └── server.py              ThreadingHTTPServer + request handler
    ├── clients/
    │   └── base.py                IntentInferenceClient — abstract interface
    ├── config/
    │   └── loader.py              AppConfig, env and prompt loading
    ├── graph/
    │   ├── engine.py              lazy LangGraph loader
    │   └── planner.py             TripPlannerGraphBuilder — compiles StateGraph
    ├── nodes/
    │   └── extract_intent.py      ExtractIntentNode — calls inference client, updates state
    └── prompts/
        └── intent_extraction.md   system prompt for structured intent extraction
```

---

## Pipeline

```
User query (CLI or POST /invoke)
    │
    ▼
TripPlannerApp.run()
    │  selects mode → creates inference client
    │
    ▼
TripPlannerGraphBuilder.invoke()
    │  compiles and runs LangGraph StateGraph
    │
    ▼
ExtractIntentNode
    │  loads prompt from core/prompts/intent_extraction.md
    │  calls IntentInferenceClient.extract_intent(prompt, user_query)
    │
    ├── mock  →  SyntheticIntentClient  (rule-based, no API)
    └── gemini →  GeminiIntentClient   (Gemini structured output, JSON schema)
    │
    ▼
IntentStruct { places, countries, start_date, end_date, budget, vibe }
    │
    ▼
TripPlannerGraphState { trip_intent, status="intent_ready", next_step="search_flights", ... }
```

---

## State

### `IntentStruct`
Structured output of the intent extraction step.

| Field | Type | Description |
|-------|------|-------------|
| `places` | `list[str]` | Destination names, e.g. `["Chamonix", "Zermatt"]` |
| `countries` | `list[str]` | Countries aligned by index with places |
| `start_date` | `str \| None` | ISO-8601 date |
| `end_date` | `str \| None` | ISO-8601 date |
| `budget` | `int \| None` | Whole number |
| `vibe` | `str` | Trip and accommodation descriptors |

### `TripPlannerGraphState`
Shared state passed between graph nodes (TypedDict for LangGraph).

| Field | Type | Initial value |
|-------|------|---------------|
| `user_query` | `str` | From request |
| `source` | `str` | `"network"` or `"cli"` |
| `status` | `str` | `"received"` |
| `trip_intent` | `IntentStruct \| None` | `None` |
| `next_step` | `str \| None` | `"extract_intent"` |
| `errors` | `list[str]` | `[]` |

---

## Extension Points

### Adding a Graph Node

Create a callable class in `core/nodes/`:

```python
from dataclasses import dataclass

@dataclass
class PrepareGeoNode:
    def __call__(self, state):
        return {
            "status": "geo_ready",
            "next_step": "search_hotels",
        }
```

Register it on the app after creation:

```python
from core.app import create_app
from core.nodes.prepare_geo import PrepareGeoNode

app = create_app()
app.append_graph_part("prepare_geo", PrepareGeoNode())
```

Nodes execute in registration order. Each node reads from the full shared state and returns only the fields it updates.

### Adding an Inference Client

Implement `IntentInferenceClient` from `core/clients/base.py` and place the implementation in `clients/`:

```python
from core.clients.base import IntentInferenceClient
from core.state import IntentStruct

class ClaudeIntentClient(IntentInferenceClient):
    def extract_intent(self, prompt: str, user_query: str) -> IntentStruct:
        ...
```

Wire it into `core/app.py` `_create_inference_client()` under a new mode name.

### Adding an API Client

Place it in `clients/` using `ApiConnector` from `clients/api_connector.py` for async HTTP with retry:

```python
from clients.api_connector import ApiConnector

class SkyscannerClient:
    def __init__(self, api_key: str) -> None:
        self._http = ApiConnector(base_url="https://skyscanner-api.example.com")
```

---

## HTTP API

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/health` | Returns `{ status, default_mode }` |
| `GET` | `/schema` | Returns JSON schema for `IntentStruct` |
| `POST` | `/invoke` | Runs the graph, returns `{ state }` |

`POST /invoke` payload:

```json
{
  "user_query": "Plan an Alps ski trip",
  "mode": "mock",
  "mock_response": { ... }
}
```

---

## Design Rules

- Each node has one responsibility. Read from shared state, return only updated fields.
- Provider-specific logic lives in `clients/`, not in nodes.
- `core/clients/base.py` is the only coupling point between core and client implementations.
- Config and prompt loading stay in `core/config/`.
- Add a test for every new node and every new client.
