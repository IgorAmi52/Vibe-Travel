# API Contract

Base URL: `http://<host>:<port>`

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/health` | `{ status, default_mode }` |
| `GET` | `/schema` | JSON schema for `IntentStruct` |
| `POST` | `/invoke` | Trip planner graph — NEW or CLARIFICATION |
| `POST` | `/flights/indicative` | Indicative flight search from origin |
| `POST` | `/flights/chains` | Roundtrip flight chain search |

## POST `/invoke`

**Request:**
```json
{
  "type": "NEW",
  "user_query": "Four days in Paris with a spa",
  "mode": "mock",
  "state": {},
  "origin_iata": "BCN",
  "destination_iata": "CDG",
  "start_date": "2026-08-10",
  "end_date": "2026-08-14",
  "budget": 1200,
  "vibe": "spa relaxing"
}
```

- `type` and `user_query` are required
- `state` is required for `CLARIFICATION` (pass back the `state` from the previous response)
- Top-level trip fields (`places`, `countries`, `start_date`, etc.) are merged into `trip_intent`

**Success response:**
```json
{
  "state": {
    "status": "travel_options_ready",
    "grouped_results": []
  }
}
```

**Clarification response:**
```json
{
  "needs_clarification": true,
  "clarification_prompt": "What are your travel dates?",
  "state": { "status": "needs_clarification", "iteration": 1 }
}
```

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

`origin_iata` is required; `outbound_date` optional (`YYYY-MM-DD`).

## POST `/flights/chains`

```json
{
  "origin_iata": "BCN",
  "destination_iata": "CDG",
  "departure_date": "2026-08-10",
  "return_date": "2026-08-14",
  "adults": 2,
  "cabin_class": "CABIN_CLASS_ECONOMY",
  "direct_only": false,
  "limit": 10
}
```

`origin_iata`, `destination_iata`, `departure_date`, `return_date` are required. `return_date >= departure_date`. `limit <= 50`.

## Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success (including clarification responses) |
| `400` | Invalid JSON, missing required field, or invalid value |
| `404` | Unknown route |
| `500` | Internal / runtime failure |
