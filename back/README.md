# Vibe Travel — Backend

Python LangGraph pipeline that extracts travel intent from a free-form query, searches flights (Skyscanner) and hotels (Booking.com), and returns vibe-ranked results via HTTP.

## Prerequisites

- Python 3.11+
- API keys for Gemini, Skyscanner, and Booking.com (only needed when not running in `mock` mode)

## Setup

```bash
cp .env.example .env
pip install -U -r requirements.txt
```

**Required env vars** (for live mode):

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Intent extraction and hotel embeddings |
| `SKYSCANNER_API_KEY` | Flight search |
| `BOOKING_RAPIDAPI_KEY` | Hotel search |

**Optional env vars** (defaults shown):

| Variable | Default | Notes |
|----------|---------|-------|
| `TRIP_PLANNER_MODE` | `mock` | `mock` (no API calls) or `gemini` |
| `TRIP_PLANNER_API_HOST` | `127.0.0.1` | Bind host |
| `TRIP_PLANNER_API_PORT` | `8080` | Bind port |
| `TRIP_PLANNER_GEMINI_MODEL` | `gemini-2.5-flash-lite` | LLM for intent extraction |
| `TRIP_PLANNER_HOTEL_VIBE_WEIGHT` | `0.7` | Composite score vibe weight |
| `SKYSCANNER_TIMEOUT_SECONDS` | `30` | Per-request timeout |
| `BOOKING_TIMEOUT_SECONDS` | `30` | Per-request timeout |

## Run

Start the HTTP API:

```bash
python3 main.py serve --host 127.0.0.1 --port 8080
```

Single invocation (mock — no API keys needed):

```bash
python3 main.py invoke --query "Plan an Alps ski trip from 2026-12-20 to 2026-12-27 for 2500" --mode mock
```

## Tests

```bash
python3 -m unittest discover -s core/tests -v
```

## Docs

- [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) — Pipeline diagram and module overview
- [`API_CONTRACT.md`](API_CONTRACT.md) — HTTP endpoints and request/response schemas
