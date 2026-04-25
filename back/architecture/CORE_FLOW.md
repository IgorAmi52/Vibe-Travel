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
| `needs_clarification` | `bool` | `False` |
| `clarification_prompt` | `str \| None` | `None` |
| `iteration` | `int` | `0` (incremented to `1` on first run) |

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

### Requesting clarification from a node

Any node can halt the pipeline by returning these two fields:

```python
def __call__(self, state):
    if not state.get("trip_intent", {}).get("start_date"):
        return {
            "needs_clarification": True,
            "clarification_prompt": "What are your travel dates?",
        }
    return {"status": "ready"}
```

The graph runs to END normally — the HTTP layer surfaces `needs_clarification` and `clarification_prompt` at the top level of the response. On the next request the frontend sends `type: "CLARIFICATION"` with the user's answer and the prior `state`; the graph re-enters at `extract_intent`.

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
| `POST` | `/invoke` | Runs the full graph from `extract_intent`, returns a success or clarification response |

### `POST /invoke` — request

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"NEW" \| "CLARIFICATION"` | yes | `NEW` starts a fresh session; `CLARIFICATION` continues after a clarification prompt |
| `user_query` | `string` | yes | Free-form travel query or the user's answer to a clarification prompt |
| `mode` | `"mock" \| "gemini"` | no | Inference backend (defaults to config) |
| `source` | `string` | no | Request origin label, default `"network"` |
| `state` | `object` | `CLARIFICATION` only | The `state` object from the previous response — carries `iteration` and prior intent |
| `mock_response` | `object` | no | Override `IntentStruct` for mock mode |

Both request types enter the graph at `extract_intent`. The graph always runs the full node chain from the beginning.

### `POST /invoke` — responses

**Success** (`200`) — pipeline completed, no clarification needed:
```json
{
  "state": {
    "status": "intent_ready",
    "trip_intent": { "places": ["Chamonix"], "start_date": "2026-12-20", ... },
    "iteration": 1
  }
}
```

**Needs clarification** (`200`) — a node broke out requesting more user input:
```json
{
  "needs_clarification": true,
  "clarification_prompt": "Could you add your travel dates and budget?",
  "state": {
    "status": "needs_clarification",
    "iteration": 1,
    ...
  }
}
```

`needs_clarification` and `clarification_prompt` are present at the top level **only** when a node signals them. Normal responses omit both keys entirely.

### Clarification loop

```
frontend                                          backend
   │                                                 │
   │  POST /invoke { type: "NEW",                    │
   │    user_query: "Alps ski trip" }                │
   │ ──────────────────────────────────────────────► │ extract_intent → ... → check_completeness
   │                                                 │   ↳ needs_clarification: true
   │ ◄────────────────────────────────────────────── │
   │  { needs_clarification: true,                   │
   │    clarification_prompt: "What are your dates?",│
   │    state: { iteration: 1, ... } }               │
   │                                                 │
   │  [show prompt to user, collect answer]          │
   │                                                 │
   │  POST /invoke { type: "CLARIFICATION",          │
   │    user_query: "20–27 Dec, budget 2500",        │
   │    state: { iteration: 1, ... } }               │
   │ ──────────────────────────────────────────────► │ extract_intent → ... → check_completeness
   │                                                 │   ↳ all criteria met
   │ ◄────────────────────────────────────────────── │
   │  { state: { status: "intent_ready",             │
   │    trip_intent: { ... }, iteration: 2 } }       │
```

This loop can repeat as many times as needed. `iteration` increments on every run and is available to all nodes via `state["iteration"]`.

---

## Design Rules

- Each node has one responsibility. Read from shared state, return only updated fields.
- Provider-specific logic lives in `clients/`, not in nodes.
- `core/clients/base.py` is the only coupling point between core and client implementations.
- Config and prompt loading stay in `core/config/`.
- Add a test for every new node and every new client.
