# Vibe-Travel Backend

## What This Is

Intent-driven travel discovery API. User describes a travel "vibe" in natural language → system extracts intent, finds flights/hotels, ranks by semantic match, and explains results.

5-stage pipeline: Intent Extraction → Candidate Generation → Hotel Matching → Ranking → Explanation

Full specs live in `docs/` (PRD, ARD) and `back/architecture/` (module-level specs like HOTEL_EMBED.md).

## Architecture

Clean architecture with three layers:

```
core/          → Domain logic, models, and interfaces (ports)
clients/       → External service implementations (adapters)
<feature>/     → Feature modules (services, routers, orchestration)
architecture/  → Specs and design docs for modules
```

### `core/`
- `core/models/` — Pydantic domain models (IntentStruct, RankedCandidate, Hotel, etc.)
- `core/api/` — Abstract interfaces (ports). Every external dependency gets an interface here first.

### `clients/`
- Concrete implementations of `core/api/` interfaces.
- Examples: `api_connector.py` (async HTTP base), Skyscanner client, Gemini embed provider.
- All clients use `httpx.AsyncClient` with retry logic.

### Feature modules (e.g., `hotel/`, `intent/`, `ranking/`)
- Each feature owns its service layer, router, and orchestration.
- Services depend on `core/api/` interfaces, never on `clients/` directly.

## Conventions

- **Python 3.12+**, FastAPI, Pydantic v2, async/await everywhere.
- **Interfaces for all external dependencies** — define in `core/api/`, implement in `clients/`.
- **Pydantic models for all data structures** — define in `core/models/`.
- **Async by default** — all I/O operations are async. Use `httpx.AsyncClient`, not `requests`.
- **Conventional commits** — `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`.
- **No dumb comments** — only comment genuinely non-obvious behavior.
- **Fail fast at boundaries** — validate API input, trust internal code.

## Key Domain Types

```python
IntentStruct:  places, countries, start_date, end_date, budget, vibe, specificity
RankedCandidate: place, hub_city, hub_entity_id, country, flight_price, hotel_score, combined_score, explanation
```

## Stack

FastAPI · Uvicorn · httpx · Pydantic · python-dotenv · numpy (embeddings)

## Environment

Copy `.env.example` → `.env`. Required: `SKY_SCANNER_KEY`.
