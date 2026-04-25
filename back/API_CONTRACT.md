# API Contract

Base URL: `http://<host>:<port>`

## GET `/health`
Returns service health.

Response:
```json
{
  "status": "ok",
  "default_mode": "mock"
}
```

## GET `/schema`
Returns the `IntentStruct` JSON schema used for intent extraction.

## POST `/invoke`
Main entrypoint for the trip planner graph.

Request:
```json
{
  "type": "NEW",
  "user_query": "Four days in paris with a spa",
  "mode": "mock",
  "source": "network",
  "state": {},
  "origin_iata": "BCN",
  "destination_iata": "CDG",
  "destination_place": "Paris",
  "person_count": 2,
  "budget": 1200,
  "places": ["Paris"],
  "countries": ["France"],
  "start_date": "2026-08-10",
  "end_date": "2026-08-14",
  "vibe": "spa center",
  "trip_intent": {},
  "mock_response": {}
}
```

Rules:
- `type`: `NEW` or `CLARIFICATION`
- `user_query`: required, non-empty
- `state`: only used for `CLARIFICATION`
- top-level `places`, `countries`, `start_date`, `end_date`, `budget`, `vibe` are merged into `trip_intent`

Response:
```json
{
  "state": {
    "status": "travel_options_ready",
    "next_step": null,
    "grouped_results": []
  }
}
```

Clarification response:
```json
{
  "state": {
    "status": "needs_clarification",
    "next_step": "search_flights",
    "clarification_prompt": "..."
  },
  "needs_clarification": true,
  "clarification_prompt": "..."
}
```

Notes:
- unfinished flow may still return `flight_results` or `hotel_results`
- finished flow returns grouped offers in `grouped_results`

## POST `/flights/indicative`
Direct indicative flight search.

Request:
```json
{
  "origin_iata": "BCN",
  "outbound_date": "2026-08-10",
  "market": "UK",
  "locale": "en-GB",
  "currency": "EUR"
}
```

Notes:
- `origin_iata` is required
- `outbound_date` is optional, but if present must be `YYYY-MM-DD`

## POST `/flights/chains`
Direct roundtrip chain search.

Request:
```json
{
  "origin_iata": "BCN",
  "destination_iata": "CDG",
  "departure_date": "2026-08-10",
  "return_date": "2026-08-14",
  "limit": 10,
  "market": "UK",
  "locale": "en-GB",
  "currency": "EUR",
  "adults": 2,
  "children_ages": [],
  "cabin_class": "CABIN_CLASS_ECONOMY",
  "direct_only": false
}
```

Rules:
- `origin_iata`, `destination_iata`, `departure_date`, `return_date` are required
- `return_date` must be on or after `departure_date`
- `limit` must be `<= 50`

## Errors
- `400`: invalid JSON, missing required field, invalid value
- `404`: unknown route
- `500`: internal/runtime failure
