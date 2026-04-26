# API Contract

Base URL: `http://<host>:<port>` (defaults to `http://127.0.0.1:8080`)

All responses are JSON. The frontend never calls these endpoints directly — it goes through the Next.js route handler at `frontend/app/api/invoke/route.ts`, which proxies to `POST /invoke`.

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET`  | `/health` | `{ status, default_mode }` |
| `GET`  | `/schema` | JSON schema for `IntentStruct` |
| `POST` | `/invoke` | Trip planner graph — `NEW` or `CLARIFICATION` |
| `POST` | `/flights/indicative` | Indicative "anywhere" flight search from a single origin |
| `POST` | `/flights/chains` | Roundtrip flight chain search |

## POST `/invoke`

**Request:**
```json
{
  "type": "NEW",
  "user_query": "Four days in Paris with a spa for two",
  "mode": "mock",
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
  "vibe": "spa relaxing"
}
```

- `type` and `user_query` are required.
- `mode` is optional; if omitted, the server uses the configured `TRIP_PLANNER_MODE` (`mock` or `gemini`).
- For `CLARIFICATION` requests, pass back the `state` from the previous response so the pipeline can apply the new query on top of the existing intent and results.
- Top-level trip fields (`places`, `countries`, `start_date`, `end_date`, `budget`, `vibe`) are merged into `trip_intent`.
- `person_count`, `budget`, `origin_iata`, `destination_iata`, and `destination_place` are also merged at the top level of the state.

**Successful response (`travel_options_ready`):**
```json
{
  "state": {
    "status": "flights_ready",
    "iteration": 1,
    "needs_clarification": false,
    "clarification_prompt": null,
    "trip_intent": {
      "places": ["Paris"],
      "countries": ["France"],
      "start_date": "2026-08-10",
      "end_date": "2026-08-14",
      "budget": 1200,
      "vibe": "spa relaxing",
      "person_count": 2
    },
    "origin_iata": "BCN",
    "destination_place": "Paris",
    "destination_iata": "CDG",
    "person_count": 2,
    "flight_results": [{"...": "..."}],
    "hotel_results": [{"...": "..."}],
    "grouped_results": [{"...": "..."}]
  }
}
```

`status` will be one of `flights_ready`, `indicative_flights_ready`, `hotels_ranked`, or `needs_clarification`. `flight_results` items carry a `destination_place` / `destination_iata` so the frontend can group results when the search fans out across multiple destinations.

**Clarification response:**
```json
{
  "needs_clarification": true,
  "clarification_prompt": "What are your travel dates?",
  "state": {
    "status": "needs_clarification",
    "iteration": 1,
    "needs_clarification": true,
    "clarification_prompt": "What are your travel dates?"
  }
}
```

The same shape is returned when a downstream node (flights, hotels) cannot continue — the prompt explains what's missing.

## POST `/flights/indicative`

```json
{
  "origin_iata": "BCN",
  "outbound_date": "2026-08-10",
  "market": "UK",
  "locale": "en-GB",
  "currency": "EUR"
}
```

`origin_iata` is required; `outbound_date` is optional (`YYYY-MM-DD`). The response is the raw Skyscanner indicative payload (`{ quotes, places, carriers, ... }`).

## POST `/flights/chains`

```json
{
  "origin_iata": "BCN",
  "destination_iata": "CDG",
  "departure_date": "2026-08-10",
  "return_date": "2026-08-14",
  "adults": 2,
  "children_ages": [],
  "cabin_class": "CABIN_CLASS_ECONOMY",
  "direct_only": false,
  "market": "UK",
  "locale": "en-GB",
  "currency": "EUR",
  "limit": 10
}
```

`origin_iata`, `destination_iata`, `departure_date`, `return_date` are required. `return_date >= departure_date`. `limit <= 50`.

**Response:**
```json
{
  "results": [
    {
      "itinerary_id": "...",
      "price_amount": 312.0,
      "price_currency": "EUR",
      "agent_name": "...",
      "deep_link": "https://..."
    }
  ],
  "count": 1
}
```

## Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success (including clarification responses) |
| `400` | Invalid JSON, missing required field, or invalid value |
| `404` | Unknown route |
| `500` | Internal / runtime failure |
