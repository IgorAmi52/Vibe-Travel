# Architecture

## Modules

| Module | Technology | Purpose |
|--------|-----------|---------|
| `main.py` | argparse | Entry point; `invoke` (single-shot) and `serve` (HTTP) commands |
| `core/app.py` | LangGraph | Assembles and runs the StateGraph pipeline (`extract_intent → search_flights → search_hotels → group_results`) |
| `core/nodes/` | LangGraph nodes | Discrete pipeline steps — each reads full state, returns only updated fields |
| `core/api/server.py` | `ThreadingHTTPServer` (stdlib) | HTTP API: `/invoke`, `/flights/indicative`, `/flights/chains`, `/health`, `/schema` |
| `core/services/` | Pydantic + NumPy | Hotel ranking orchestration: fetch → embed → score → rank |
| `core/config/` | python-dotenv-style loader | Loads env vars and the LLM prompt file |
| `core/clients/` | httpx | Skyscanner indicative + live flight clients, mock flight client |
| `clients/` | httpx, Gemini SDK | Infrastructure adapters: Gemini LLM/embeddings, Booking.com (RapidAPI), mock |
| `core/api/embed_provider.py` | Abstract interface | Domain port for embedding providers |
| `core/api/hotel_api_client.py` | Abstract interface | Domain port for hotel API clients (Booking, fixtures) |
| `core/models/hotel.py` | Pydantic | `Hotel`, `ScoredHotel`, `HotelContent`, `HotelReview`, `HotelSearchResult` |
| `clients/gemini_embed_provider.py` | Gemini `gemini-embedding-001` | Generates embeddings for hotel text blobs and the vibe query |
| `clients/cosine_similarity_service.py` | NumPy | Computes cosine similarity between vibe and hotel embeddings |
| `clients/booking_client.py` | httpx + RapidAPI | Booking.com autosuggest, search, content, description, and reviews |

## Pipeline

```
User query (CLI or POST /invoke)
         │
         ▼
ExtractIntentNode   ──── Gemini structured output / mock
         │               → IntentStruct { places, countries, dates, budget, vibe, person_count }
         │               (halts with clarification if intent is incomplete)
         ▼
SearchFlightsNode   ──── Skyscanner API
         │               1. Resolve every IntentStruct.place → IATA via autosuggest
         │               2. Fan out: roundtrip indicative search per resolved destination
         │               3. Tag each quote with destination_place / destination_iata
         │               4. Scale per-person prices to person_count
         │               → flight_results (one or many destinations)
         ▼
SearchHotelsNode    ──── Booking.com + Gemini embeddings
         │
         │   For every unique destination_place from flight_results:
         │            │
         │            ▼
         │   Booking autosuggest → entity (city / region / district / landmark / country)
         │            │
         │            ▼
         │   searchHotels for the resolved entity + check-in/out dates
         │            │
         │            ▼
         │   Drop properties with no availability for those dates
         │            │
         │            ▼
         │   Content + description + reviews per hotel (parallel)
         │            │
         │            ▼
         │   Build text blob: description + amenities + review texts
         │            │
         │            ▼
         │   Embed vibe query + hotel blobs (Gemini gemini-embedding-001)
         │            │
         │            ▼
         │   composite_score = 0.7 × vibe_similarity + 0.2 × price_score + 0.1 × guest_rating
         │            │
         │            ▼
         │   Ranked hotel list per destination
         ▼
GroupResultsNode    ──── domain logic
                         → grouped_results (flight + hotel pairs grouped by destination)
```

Any node can halt the pipeline by returning `needs_clarification: true`; the HTTP layer surfaces `clarification_prompt` to the frontend, which re-submits with `type: CLARIFICATION` and the prior `state`. Hotel ranking weights are configurable via `TRIP_PLANNER_HOTEL_VIBE_WEIGHT`, `TRIP_PLANNER_HOTEL_PRICE_WEIGHT`, and `TRIP_PLANNER_HOTEL_RATING_WEIGHT`.

## State carried across turns

`TripPlannerGraphState` is a `TypedDict` containing the user query, normalized `trip_intent` (`IntentStruct`), resolved `origin_iata` / `destination_place` / `destination_iata`, `person_count`, `flight_results`, `hotel_results`, `grouped_results`, plus pipeline metadata (`status`, `next_step`, `iteration`, `needs_clarification`, `clarification_prompt`). The frontend echoes this `state` back on every clarification turn so refinements apply on top of the previous result set rather than starting from scratch.
