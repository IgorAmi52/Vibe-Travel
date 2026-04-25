# Vibe Travel — Backend

## Install

```bash
pip install -U -r requirements.txt
```

## Environment

Copy `.env.example` to `.env` and fill in your values:

```
GEMINI_API_KEY=your_gemini_api_key_here
TRIP_PLANNER_MODE=mock
TRIP_PLANNER_API_HOST=127.0.0.1
TRIP_PLANNER_API_PORT=8080
TRIP_PLANNER_GEMINI_MODEL=gemini-2.5-flash-lite
TRIP_PLANNER_PROMPT_PATH=core/prompts/intent_extraction.md
```

## Run

Single invocation with mock data:

```bash
python3 main.py invoke --query "Plan an Alps ski trip from 2026-12-20 to 2026-12-27 for 2500" --mode mock
```

Single invocation with Gemini:

```bash
python3 main.py invoke --query "Plan an Alps ski trip" --mode gemini
```

Start the HTTP API:

```bash
python3 main.py serve --host 127.0.0.1 --port 8080
```

Example request:

```bash
curl -X POST http://127.0.0.1:8080/invoke \
  -H 'Content-Type: application/json' \
  -d '{"user_query": "Plan an Alps ski trip", "mode": "mock"}'
```

## Tests

```bash
python3 -m unittest discover -s core/tests -v
```

## Architecture

- [`architecture/CORE_FLOW.md`](architecture/CORE_FLOW.md) — LangGraph pipeline, state schema, HTTP API, and how to add nodes or inference clients.
- [`architecture/HOTEL_EMBED.md`](architecture/HOTEL_EMBED.md) — Hotel embedding and vibe-based ranking module: Skyscanner API flow, embedding strategy, and composite scoring.
