# Trip Planner Core

This module provides the minimal LangGraph-style core for the travel planner.
It requires the real `langgraph` package.

It currently has one graph node:
- `extract_intent`: reads the user query, loads the prompt from `core/prompts/intent_extraction.md`, and returns a structured `IntentStruct`.

The module can run in two modes:
- `mock`: uses synthetic or injected test data
- `gemini`: calls Gemini with structured output

## Structure

- `core/app.py`: central app entry point, graph assembly, and runtime
- `core/config/`: config and prompt loading
- `core/graph/`: graph builder and real LangGraph loader
- `core/nodes/`: single-responsibility graph nodes
- `core/clients/`: inference backends such as Gemini and mock
- `core/api.py`: small HTTP API
- `core/main.py`: CLI entry point

## Environment

The module reads these variables from `.env`:

- `GEMINI_API_KEY`
- `TRIP_PLANNER_MODE`
- `TRIP_PLANNER_API_HOST`
- `TRIP_PLANNER_API_PORT`
- `TRIP_PLANNER_GEMINI_MODEL`
- `TRIP_PLANNER_PROMPT_PATH`

## Install

```bash
pip install -U -r requirements.txt
```

## Run It

Invoke once with mock data:

```bash
python3 -m core.main invoke --query "Plan an Alps ski trip from 2026-12-20 to 2026-12-27 for 2500" --mode mock
```

Invoke once with Gemini:

```bash
python3 -m core.main invoke --query "Plan an Alps ski trip" --mode gemini
```

Start the API:

```bash
python3 -m core.main serve --host 127.0.0.1 --port 8080
```

Example API request:

```bash
curl -X POST http://127.0.0.1:8080/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "user_query": "Plan an Alps ski trip",
    "mode": "mock"
  }'
```

## State

The main intent payload is `IntentStruct` from `core/state.py`:

```python
class IntentStruct:
    places: list[str]
    countries: list[str]
    start_date: str | None
    end_date: str | None
    budget: int | None
    vibe: list[str]
```

This becomes `trip_intent` inside the graph state, together with:
- `user_query`
- `source`
- `status`
- `next_step`
- `errors`

## Extend The Graph

Add a new node in `core/nodes/` with one responsibility.

Example:

```python
from dataclasses import dataclass

@dataclass
class PrepareGeoNode:
    def __call__(self, state):
        trip_intent = state["trip_intent"]
        return {
            "status": "geo_ready",
            "next_step": "search_hotels",
        }
```

Register it in the app:

```python
from core.app import create_app
from core.nodes.prepare_geo import PrepareGeoNode

app = create_app()
app.append_graph_part("prepare_geo", PrepareGeoNode())
```

The execution order matches the order of `append_graph_part(...)`.

## Extension Rules

- Keep each node focused on one step only.
- Read from the shared state and return only the fields your node updates.
- Put provider-specific logic in `core/clients/`, not in nodes.
- Put loading/config logic in `core/config/`.
- Add tests when you add a node or a new client.

## Tests

Run:

```bash
python3 -m unittest discover -s core/tests -v
```
