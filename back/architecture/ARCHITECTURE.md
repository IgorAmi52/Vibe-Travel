# Architecture

## Modules

| Module | Technology | Purpose |
|--------|-----------|---------|
| `main.py` | argparse | Entry point; `invoke` (single-shot) and `serve` (HTTP) commands |
| `core/app.py` | LangGraph | Assembles and runs the StateGraph pipeline |
| `core/nodes/` | LangGraph nodes | Discrete pipeline steps — each reads full state, returns only updated fields |
| `core/api/server.py` | ThreadingHTTPServer | HTTP API: `/invoke`, `/flights/*`, `/hotels/*`, `/health` |
| `core/services/` | Pydantic + NumPy | Hotel ranking orchestration: fetch → embed → score → rank |
| `core/config/` | python-dotenv | Loads env vars and LLM prompt files |
| `clients/` | httpx, Gemini SDK | Infrastructure adapters: Gemini LLM/embeddings, Skyscanner, Booking.com, mock |
| `core/api/embed_provider.py` | Abstract interface | Domain port for embedding providers |
| `core/models/hotel.py` | Pydantic | Hotel, ScoredHotel, HotelContent, HotelReview data models |
| `clients/gemini_embed_provider.py` | Gemini `text-embedding-004` | Generates embeddings for hotel text blobs and vibe query |
| `clients/cosine_similarity_service.py` | NumPy | Computes cosine similarity between vibe and hotel embeddings |
| `clients/booking_client.py` | httpx + RapidAPI | Fetches hotel content and reviews from Booking.com |

## Pipeline

```
User query (CLI or POST /invoke)
         │
         ▼
ExtractIntentNode   ──── Gemini structured output / mock
         │               → IntentStruct { places, dates, budget, vibe }
         ▼
SearchFlightsNode   ──── Skyscanner API
         │               → flight chains (roundtrip options)
         ▼
SearchHotelsNode    ──── Booking.com + Gemini embeddings
         │
         │   Vibe query + destination
         │            │
         │            ▼
         │   Booking.com autosuggest  →  hotel entity IDs
         │            │
         │            ▼
         │   Content + Reviews per hotel (parallel)
         │            │
         │            ▼
         │   Build text blob: description + amenities + review texts
         │            │
         │            ▼
         │   Embed vibe query + hotel blobs  (Gemini text-embedding-004)
         │            │
         │            ▼
         │   composite_score = 0.7 × vibe_similarity + 0.2 × price_score + 0.1 × guest_rating
         │            │
         │            ▼
         │   Ranked hotel list
         ▼
GroupResultsNode    ──── domain logic
                         → grouped_results (flight + hotel pairs)
```

Nodes can halt the pipeline by returning `needs_clarification: true`; the HTTP layer surfaces `clarification_prompt` to the frontend, which re-submits with `type: CLARIFICATION` and the prior `state`. Hotel ranking weights are configurable via `TRIP_PLANNER_HOTEL_VIBE_WEIGHT`, `_PRICE_WEIGHT`, and `_RATING_WEIGHT`.
