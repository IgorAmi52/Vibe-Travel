# Hotel Embedding & Ranking Module

## Intent

This module ranks hotels based on how well they match a user's desired "vibe." It sits in the middle of a larger pipeline — receiving processed vibe keywords from upstream and outputting a ranked hotel list to a downstream reranker.

## Input / Output Contract

**Input:**
- A string or list of keywords representing the user's vibe (e.g., `"quiet relaxing pool"`)
- Search parameters: destination, check-in/check-out dates, guests

**Output:**
- Ranked list of hotels, each containing:
  - Hotel ID, name, and metadata
  - Vibe similarity score (cosine similarity)
  - Price score (normalized)
  - Guest rating score (normalized)
  - Composite rank score
- Passed downstream to the reranker module

## Data Source — Skyscanner Hotels API (via RapidAPI)

We use four Skyscanner endpoints:

| # | Endpoint | Method | Purpose | Key Data |
|---|----------|--------|---------|----------|
| 1 | **Autosuggest** (`/v1/hotels/autosuggest`) | POST | Resolve destination text to entity IDs | `entityId`, name, type, coordinates |
| 2 | **Live Pricing** (`/v1/hotels/search` + polling) | POST + GET | Discover hotels for a destination + dates | `hotelId`, name, price, room types, availability |
| 3 | **Content** (`/v1/hotels/content`) | POST | Static hotel details per hotelId | Description, amenities, star rating, guest rating, images, policies |
| 4 | **Reviews** (`/v1/hotels/reviews`) | POST | Guest reviews per hotelId | Review text, ratings, guest type tags |

**Key point:** Live Pricing is the only endpoint that returns a list of hotels for a destination. Content and Reviews both require a `hotelId` obtained from Live Pricing.

### Rate Limits

| API | Per Second | Per Minute | Per Hour |
|-----|-----------|-----------|---------|
| Autosuggest | 50 | 300 | 18,000 |
| Live Pricing (create) | 20 | 100 | 6,000 |
| Live Pricing (poll) | 200 | 1,000 | 60,000 |
| Content | 50 | 300 | 18,000 |
| Reviews | 50 | 300 | 18,000 |

## Pipeline

```
User Input (vibe keywords + destination + dates + guests)
    │
    ▼
1. Autosuggest  →  resolve destination to entityId
    │
    ▼
2. Live Pricing  →  discover hotels (hotelIds + prices) for destination/dates
    │
    ▼
3. Content + Reviews (parallel per hotel)
   Content  →  description, amenities, star rating, guest rating
   Reviews  →  top N guest review texts
    │
    ▼
4. Build text blob per hotel:  description + amenities keywords + review texts
    │
    ▼
5. Embed vibe query + hotel text blobs  (Gemini text-embedding-004)
    │
    ▼
6. Cosine similarity + composite scoring
    │
    ▼
7. Return ranked list → downstream reranker
```

### Step 1: Resolve Destination
- Call Autosuggest with user's destination text
- Extract `entityId` for the top match

### Step 2: Discover Hotels
- Call Live Pricing with `entityId`, check-in/check-out dates, and guest count
- This is an async endpoint: create search → poll until results are ready
- Returns hotel IDs, names, and prices

### Step 3: Fetch Hotel Data (parallel)
- For each hotel from Step 2, fetch Content and Reviews in parallel
- **Content:** hotel description (rich text), amenities array, star rating, guest rating, accommodation type
- **Reviews:** top N review texts sorted by recommended, with guest type and rating info

### Step 4: Build Embeddable Text
- Concatenate per hotel: `{description} {amenities as keywords} {review_1} {review_2} ... {review_N}`
- This text blob captures both how the hotel presents itself (description + amenities) and how guests actually experienced it (reviews)

### Step 5: Embedding & Similarity
- Generate embeddings for each hotel's text blob using Gemini `text-embedding-004`
- Generate embedding for the vibe input string
- Compute cosine similarity between vibe embedding and each hotel embedding

### Step 6: Composite Scoring

```
composite_score = (w1 * vibe_similarity) + (w2 * normalized_price_score) + (w3 * normalized_guest_rating)
```

- `vibe_similarity` — cosine similarity (0 to 1)
- `normalized_price_score` — inverted and normalized (cheaper = higher score)
- `normalized_guest_rating` — guest rating normalized to 0–1 scale
- Weights (`w1`, `w2`, `w3`) are configurable, default emphasis on vibe similarity

### Step 7: Output
- Sort by composite score descending
- Return ranked list to the reranker

## What Gets Embedded — Signal Tiers

| Tier | Field | Source API | Why |
|------|-------|-----------|-----|
| 1 (highest) | Hotel description | Content | Curated narrative — how the hotel wants to be perceived |
| 1 | Review texts | Reviews | Ground truth — how guests actually experienced the vibe |
| 1 | Amenities | Content | Hard features that define experience (pool, spa, gym → vibe signals) |
| 2 (supporting) | Accommodation type | Content | Property category (boutique, resort, budget) |
| 2 | Star rating | Content | Quality tier — feeds composite score, not embedding |
| 2 | Guest rating | Content | Satisfaction signal — feeds composite score |
| 3 (contextual) | Price | Live Pricing | Feeds composite score only, not embedded |

**Tier 1 fields are concatenated into the text blob for embedding. Tier 2–3 feed the composite scoring formula as numeric signals.**

## Module Structure

```
back/
├── core/
│   ├── api/                               (interfaces for external API clients)
│   │   └── embed_provider.py              (EmbedProvider interface — domain port)
│   └── models/
│       └── hotel.py                       (Hotel, HotelRankingResult, Skyscanner DTOs)
├── clients/
│   ├── api_connector.py                   (exists — async HTTP client with retry)
│   ├── gemini_embed_provider.py           (Gemini embedding implementation)
│   └── skyscanner_client.py               (wraps ApiConnector for all 4 endpoints)
├── hotel/
│   ├── hotel_embedding_service.py         (builds hotel text blobs + calls embed provider)
│   ├── hotel_ranking_service.py           (orchestrator: fetch → embed → score → rank)
│   └── router.py                          (FastAPI endpoint)
```

## Tech Stack

| Component | Choice | Notes |
|-----------|--------|-------|
| Embeddings | **Gemini** (`text-embedding-004`) | On-the-fly generation per request |
| Backend | **FastAPI** | Already in place |
| HTTP Client | **httpx** (via `api_connector.py`) | Existing async client with retry logic |
| Similarity | **numpy** | Cosine similarity computation |
| Models | **Pydantic** | Request/response validation |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hotel discovery | Live Pricing API | Only endpoint that returns hotels for a destination — Content/Reviews require hotelId |
| Embedding text | Description + amenities + reviews | Reviews are ground truth for vibe; description is how hotel presents itself; amenities map to concrete vibe signals |
| Embedding computation | On-the-fly | Start simple; migrate to vector DB when performance requires it |
| Embed provider interface | `core/api/` package | Domain port — generic enough for reuse, kept out of infrastructure layer |
| Gemini implementation | `clients/` package | Infrastructure adapter — generic, no domain knowledge |
| Filtering strategy | Hybrid | Amenities/ratings as hard filters, embeddings for subjective vibe matching |

## Future Considerations

- **Vector DB migration** — pre-compute and store hotel embeddings in Qdrant or pgvector for faster lookups at scale
- **LLM vibe summaries** — use Gemini to distill reviews into a concise "vibe profile" before embedding for higher signal quality
- **Caching layer** — cache embeddings per hotel to avoid recomputation across requests for the same destination
- **Review filtering** — weight reviews by guest type matching the current user's profile for more personalized vibe matching
