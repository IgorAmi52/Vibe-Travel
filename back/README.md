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
SKYSCANNER_BASE_URL=https://skyscanner89.p.rapidapi.com
SKYSCANNER_API_KEY=your_rapidapi_key_here
SKYSCANNER_API_HOST=skyscanner89.p.rapidapi.com
SKYSCANNER_TIMEOUT_SECONDS=30
SKYSCANNER_MAX_RETRIES=3
SKYSCANNER_RETRY_DELAY_SECONDS=1
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

New request:

```bash
curl -X POST http://127.0.0.1:8080/invoke \
  -H 'Content-Type: application/json' \
  -d '{"type": "NEW", "user_query": "Plan an Alps ski trip", "mode": "mock"}'
```

If the response contains `needs_clarification: true`, show `clarification_prompt` to the user and send their answer as a `CLARIFICATION` request, passing the prior `state` back:

```bash
curl -X POST http://127.0.0.1:8080/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "CLARIFICATION",
    "user_query": "Dec 20–27, budget 2500",
    "mode": "mock",
    "state": <state from previous response>
  }'
```

Flight roundtrip chains (Skyscanner):

```bash
curl -X POST http://127.0.0.1:8080/flights/chains \
  -H 'Content-Type: application/json' \
  -d '{
    "origin_iata": "VIE",
    "destination_iata": "LON",
    "departure_date": "2026-06-10",
    "return_date": "2026-06-15",
    "adults": 1,
    "direct_only": true,
    "limit": 5
  }'
```

Required fields for `/flights/chains`:
- `origin_iata` (string)
- `destination_iata` (string)
- `departure_date` (ISO date `YYYY-MM-DD`)
- `return_date` (ISO date `YYYY-MM-DD`, must be on or after `departure_date`)

Optional fields:
- `market` (default `UK`)
- `locale` (default `en-GB`)
- `currency` (default `EUR`)
- `adults` (default `1`)
- `children_ages` (array of integers, default `[]`)
- `cabin_class` (default `CABIN_CLASS_ECONOMY`)
- `direct_only` (boolean, default `false`)
- `limit` (integer, default `10`, max `50`)

## Tests

```bash
python3 -m unittest discover -s core/tests -v
```

## Architecture

- [`architecture/CORE_FLOW.md`](architecture/CORE_FLOW.md) — LangGraph pipeline, state schema, HTTP API, and how to add nodes or inference clients.
- [`architecture/HOTEL_EMBED.md`](architecture/HOTEL_EMBED.md) — Hotel embedding and vibe-based ranking module: Skyscanner API flow, embedding strategy, and composite scoring.
