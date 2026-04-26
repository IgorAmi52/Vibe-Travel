# Vibe Travel — Backend

Python LangGraph pipeline that extracts travel intent from a free-form query, fans out across every candidate destination to search flights (Skyscanner) and hotels (Booking.com via RapidAPI), ranks hotels by vibe similarity (Gemini embeddings), and returns the grouped results over HTTP.

## Prerequisites

- Python 3.11+
- API keys for Gemini, Skyscanner, and Booking.com (only needed when not running in `mock` mode)

## Setup

```bash
cp .env.example .env
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -U -r requirements.txt
```

**Required env vars** (for live mode):

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Intent extraction and hotel embeddings |
| `SKYSCANNER_API_KEY` | Flight search (Skyscanner Partners API) |
| `BOOKING_RAPIDAPI_KEY` | Hotel search (Booking.com via RapidAPI) |

**Optional env vars** (defaults shown):

| Variable | Default | Notes |
|----------|---------|-------|
| `TRIP_PLANNER_MODE` | `mock` | `mock` (no API calls) or `gemini` |
| `TRIP_PLANNER_API_HOST` | `127.0.0.1` | Bind host |
| `TRIP_PLANNER_API_PORT` | `8080` | Bind port |
| `TRIP_PLANNER_GEMINI_MODEL` | `gemini-2.5-flash-lite` | LLM for intent extraction |
| `TRIP_PLANNER_GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model for hotel ranking |
| `TRIP_PLANNER_HOTEL_VIBE_WEIGHT` | `0.7` | Composite score: vibe weight |
| `TRIP_PLANNER_HOTEL_PRICE_WEIGHT` | `0.2` | Composite score: price weight |
| `TRIP_PLANNER_HOTEL_RATING_WEIGHT` | `0.1` | Composite score: guest-rating weight |
| `TRIP_PLANNER_HOTEL_CURRENCY` | `USD` | Currency code passed to Booking.com |
| `SKYSCANNER_TIMEOUT_SECONDS` | `30` | Per-request timeout |
| `BOOKING_TIMEOUT_SECONDS` | `30` | Per-request timeout |

## Run

Start the HTTP API:

```bash
python3 main.py serve --host 127.0.0.1 --port 8080
```

Single invocation (mock — no API keys needed):

```bash
python3 main.py invoke \
  --query "Plan an Alps ski trip from 2026-12-20 to 2026-12-27 for 2500" \
  --mode mock
```

Logs are written to `logs/trip_planner.log` (rotating, 2 MB per file, 3 backups) and mirrored to stdout.

## Tests

```bash
python3 -m unittest discover -s core/tests -v
```

The suite covers intent extraction (mock + Gemini SDK contract), flight search (multi-destination fan-out, indicative roundtrip, price scaling for `person_count`), hotel ranking (autosuggest fallback across destination types, availability filtering), and graph wiring.

## Docs

- [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) — Pipeline diagram and module overview
- [`API_CONTRACT.md`](API_CONTRACT.md) — HTTP endpoints and request/response schemas
- [`core/prompts/intent_extraction.md`](core/prompts/intent_extraction.md) — System prompt used for the Gemini intent extractor
