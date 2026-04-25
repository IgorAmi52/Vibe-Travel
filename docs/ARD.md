# ARD — Intent-Driven Travel Discovery
**Version:** 0.1  
**Status:** Draft  
**Authors:** Hackathon team  

---

## 1. System overview

Five-stage pipeline triggered by a single user query. Stages 1–4 run server-side on each query or refinement turn. Stage 5 (explanation) runs last, after ranking is complete.

```
User query
    │
    ▼
[Stage 1] Intent extraction          LLM — one call, returns IntentStruct
    │
    ▼
[Stage 2] Candidate generation       Skyscanner APIs — Autosuggest + Indicative
    │
    ▼
[Stage 3] Hotel matching             Pre-stored embeddings + keyword scoring
    │
    ▼
[Stage 4] Ranking                    Scoring function — no LLM
    │
    ▼
[Stage 5] Explanation                LLM — one call, returns annotated candidates
    │
    ▼
Response to client
```

Refinement turns re-enter at stage 1 with the existing IntentStruct as context — the LLM produces a diff, not a full re-extraction.

---

## 2. Shared types

All modules must conform to these types. Change requests require agreement from all four team members.

```python
class IntentStruct:
    places: list[str]        # specific named places matching the vibe
    countries: list[str]     # corresponding countries — metadata only
    start_date: str | None   # ISO date string
    end_date: str | None     # ISO date string
    budget: int | None       # total trip budget in EUR
    vibe: list[str]          # destination + accommodation character tags
    specificity: str         # "exploratory" | "directional" | "specific"

class RankedCandidate:
    place: str               # display label e.g. "Dolomites"
    hub_city: str            # nearest airport city e.g. "Venice"
    hub_entity_id: str       # Skyscanner entity ID
    country: str
    indicative_flight_price: float | None
    hotel_match_score: float | None
    indicative_hotel_price: float | None
    combined_score: float
    cheapest_month: str | None
    shallow_link: str | None
    explanation: str | None
```

---

## 3. Stage 1 — Intent extraction

**Owner:** Person 1  
**Input:** raw query string + optional existing IntentStruct (for refinement turns)  
**Output:** IntentStruct  
**Model:** claude-sonnet-4-20250514 or gpt-4o  
**Latency target:** < 3s  

### 3.1 Initial extraction prompt

```
You are a travel intent parser. Given a user's natural language travel query, 
extract a structured intent object.

Rules:
- Deduce vibe first, then use vibe to generate places that embody it
- Places must be specific named areas, valleys, resorts or towns — not countries
- Each place must have a corresponding country
- Budget is always in EUR — convert if user specifies another currency
- Classify specificity:
    "exploratory" — destination is open or vague
    "directional" — destination clear, dates or budget missing
    "specific"    — destination + dates + budget all present
- If a field cannot be deduced, set it to null

Return only valid JSON matching this schema:
{
  "places": string[],
  "countries": string[],
  "start_date": string | null,
  "end_date": string | null,
  "budget": number | null,
  "vibe": string[],
  "specificity": "exploratory" | "directional" | "specific"
}

Query: {user_query}
```

### 3.2 Refinement diff prompt

```
You are updating a travel intent struct based on a user's follow-up message.

Current intent:
{current_intent_json}

User refinement: "{refinement_message}"

Return a partial JSON object containing ONLY the fields that should change.
Do not repeat unchanged fields. If a field should be cleared, set it to null.

Examples:
- "narrow to north of Italy" → {"places": [...italian places...], "countries": ["Italy"]}
- "direct flights only" → {"direct_only": true}
- "make it cheaper" → {"budget": <reduced value or null if unknown>}
```

### 3.3 Exposed interface

```python
def extract_intent(query: str) -> IntentStruct
def diff_intent(current: IntentStruct, refinement: str) -> dict  # partial update
def apply_diff(current: IntentStruct, diff: dict) -> IntentStruct
```

### 3.4 Testing approach

Unit test with fixed queries. No API calls needed — mock the LLM response. Cover:
- Vague query with no dates or budget
- Query with budget in non-EUR currency
- Refinement that removes a country
- Refinement that adds a date constraint

---

## 4. Stage 2 — Candidate generation

**Owner:** Person 2  
**Input:** IntentStruct  
**Output:** list of (place, hub_city, hub_entity_id, indicative_flight_price)  
**Latency target:** < 4s (parallel API calls)  

### 4.1 Step 1 — Resolve places to hub entity IDs

For each place in IntentStruct.places, call Autosuggest to find the nearest hub city entity ID.

```
POST /v3/autosuggest/flights
{
  "query": {
    "market": "{market}",
    "locale": "{locale}",
    "searchTerm": "{place}",
    "includedEntityTypes": ["PLACE_TYPE_CITY", "PLACE_TYPE_AIRPORT"]
  }
}
```

Take the first result. Store mapping: place → (hub_city, hub_entity_id).

Multiple places may resolve to the same hub (Ötztal and Stubai both resolve to Innsbruck). Deduplicate hub entity IDs before calling Indicative — call each hub once, then fan results back to all places that share it.

### 4.2 Step 2 — Indicative prices per hub

For each unique hub entity ID, call Indicative with anytime flag. Parallel calls.

```
POST /v3/flights/indicative/search
{
  "query": {
    "currency": "EUR",
    "locale": "{locale}",
    "market": "{market}",
    "queryLegs": [{
      "originPlace": { "queryPlace": { "entityId": "{origin_entity_id}" } },
      "destinationPlace": { "queryPlace": { "entityId": "{hub_entity_id}" } },
      "dateRange": {
        "startDate": { "year": {year}, "month": {month} },
        "endDate":   { "year": {year}, "month": {month} }
      }
    }]
  }
}
```

If IntentStruct.start_date is set, use that month. If null, use anytime: true.

### 4.3 Step 3 — Date aggregation (on demand)

Called when user requests cheapest month for a specific result. Not part of main query path.

```
POST /v3/flights/indicative/search
{
  "query": {
    "dateTimeGroupingType": "DATE_TIME_GROUPING_TYPE_BY_MONTH",
    "queryLegs": [{
      "originPlace": ...,
      "destinationPlace": { "queryPlace": { "entityId": "{hub_entity_id}" } },
      "dateRange": {
        "startDate": { "year": 2025, "month": 1 },
        "endDate":   { "year": 2025, "month": 12 }
      }
    }]
  }
}
```

### 4.4 Step 4 — Shallow link generation

Called when a candidate is confirmed (UC2) or user clicks CTA.

```
GET /refer/flights/live/dayview
  ?origin={origin_iata}
  &destination={hub_iata}
  &departuredate={start_date}
  &returndate={end_date}
  &usercountry={market}
  &userlanguage={locale}
  &associateid={associate_id}
  &nonstop={true if direct_only}
```

### 4.5 Culture resolution

Called once per session on startup. Results cached for session lifetime.

```
GET /v3/culture/currencies
GET /v3/culture/markets
```

### 4.6 Exposed interface

```python
def resolve_hubs(places: list[str], market: str, locale: str) -> dict[str, HubResult]
def get_indicative_prices(origin_id: str, hub_ids: list[str], date_range: DateRange) -> dict[str, float]
def get_cheapest_month(origin_id: str, hub_id: str) -> list[MonthPrice]
def get_shallow_link(origin_iata: str, dest_iata: str, params: SearchParams) -> str
```

### 4.7 Error handling

- Autosuggest returns no match → log, set hub_entity_id = null, pass through to ranking with null price
- Indicative returns no results for a hub → set indicative_flight_price = null
- Indicative API timeout (> 5s) → return partial results for hubs that responded

---

## 5. Stage 3 — Hotel matching

**Owner:** Person 3  
**Input:** list of (place, hub_entity_id) + IntentStruct.vibe  
**Output:** list of (place, hotel_match_score, indicative_hotel_price)  
**Latency target:** < 1s (all vectors pre-stored, query time is dot products only)  

### 5.1 Offline pipeline (pre-built before demo)

Run once. Output stored in `/embeddings/`.

```
For each destination in corpus:
  1. Fetch hotel reviews and descriptions via Hotels Reviews + Hotels Content API
  2. Split reviews into sentences
  3. Run VADER sentiment on each sentence
  4. Bucket into positive_sentences and negative_sentences
  5. Extract keywords per sentiment bucket using KEYWORD_DICT
  6. Build property signal: { confirmed: [...], denied: [...] }
  7. Construct enriched description: "{property_name}. {confirmed_keywords joined}. No: {denied_keywords joined}"
  8. Embed enriched description using text-embedding-3-small
  9. Store: { place: str, embedding: float[], keyword_signals: dict, avg_hotel_price: float }
```

Output file: `/embeddings/destinations.json`

```json
[
  {
    "place": "Dolomites",
    "hub": "Venice",
    "embedding": [0.023, -0.041, ...],
    "keyword_signals": {
      "confirmed": ["hiking", "mountain views", "quiet", "rural"],
      "denied": ["crowded", "noisy"]
    },
    "avg_hotel_price": 120
  }
]
```

### 5.2 Keyword dictionary

```python
KEYWORD_DICT = {
    "rural":        ["countryside", "village", "farm", "meadow", "remote", "local"],
    "nature":       ["hiking", "trails", "forest", "mountains", "scenic", "wildlife"],
    "quiet":        ["peaceful", "quiet", "tranquil", "empty", "uncrowded", "serene"],
    "crowd_high":   ["touristy", "crowded", "busy", "packed", "loud"],
    "ski":          ["ski-in", "ski-out", "slopes", "piste", "gondola", "après-ski"],
    "urban":        ["city centre", "nightlife", "bars", "shopping", "metro"],
    "food":         ["restaurant", "local food", "cuisine", "market", "farm to table"],
    "beach":        ["beachfront", "ocean view", "sandy", "coastal", "swimming"],
    "cosy":         ["fireplace", "cosy", "charming", "intimate", "homely"],
    "luxury":       ["spa", "pool", "concierge", "five-star", "suite"]
}
```

### 5.3 Query time scoring

```python
def score_destination(place: str, vibe: list[str]) -> float:
    stored = load_embedding(place)           # O(1) lookup from pre-stored dict
    query_text = " ".join(vibe)
    query_vector = embed(query_text)         # single embed call per query

    # embedding similarity
    sem_score = cosine_similarity(query_vector, stored["embedding"])

    # keyword score
    kw_score = 0.0
    relevant_keywords = flatten([KEYWORD_DICT.get(v, []) for v in vibe])
    for kw in relevant_keywords:
        if kw in stored["keyword_signals"]["confirmed"]:
            kw_score += 1.0
        if kw in stored["keyword_signals"]["denied"]:
            kw_score -= 0.5
    kw_score = normalise(kw_score, len(relevant_keywords))

    return 0.6 * sem_score + 0.4 * kw_score

def score_all(candidates: list[str], vibe: list[str]) -> dict[str, float]:
    query_vector = embed(" ".join(vibe))     # embed once, reuse for all candidates
    return { place: score_with_vector(place, query_vector) for place in candidates }
```

### 5.4 Hotels Indicative (UC2 only)

For specificity = specific, fetch indicative hotel prices per destination to check against budget.

```
POST /v3/hotels/indicative/search
{ "entityId": "{hub_entity_id}", "checkIn": "{start_date}", "checkOut": "{end_date}" }
```

### 5.5 Exposed interface

```python
def score_all(places: list[str], vibe: list[str]) -> dict[str, float]
def get_hotel_indicative(hub_entity_id: str, check_in: str, check_out: str) -> float | None
def load_corpus() -> dict  # loads /embeddings/destinations.json into memory on startup
```

---

## 6. Stage 4 — Ranking

**Owner:** Person 3  
**Input:** candidates with flight prices and hotel scores  
**Output:** ordered list[RankedCandidate]  

### 6.1 Scoring function

```python
def rank(candidates: list, intent: IntentStruct) -> list[RankedCandidate]:
    scored = []
    for c in candidates:
        hotel_score  = c.hotel_match_score or 0.0
        price_score  = price_fit(c.indicative_flight_price, c.indicative_hotel_price, intent.budget)
        avail_score  = 0.0 if c.indicative_flight_price is None else 1.0

        combined = (
            0.5 * hotel_score +
            0.35 * price_score +
            0.15 * avail_score
        )
        scored.append({ **c, "combined_score": combined })

    return sorted(scored, key=lambda x: x["combined_score"], reverse=True)

def price_fit(flight: float | None, hotel: float | None, budget: int | None) -> float:
    if budget is None:
        return 1.0  # no budget constraint — neutral score
    total = (flight or 0) + (hotel or 0)
    if total == 0:
        return 0.5
    ratio = total / budget
    if ratio <= 0.8:   return 1.0   # comfortably within budget
    if ratio <= 1.0:   return 0.7   # within budget
    if ratio <= 1.2:   return 0.3   # slightly over
    return 0.0                       # significantly over
```

Candidates are never excluded — they are always ranked lower. The UI applies a visual indicator for over-budget results.

### 6.2 Specificity routing

```python
if intent.specificity == "specific":
    # require both flight and hotel prices before scoring
    # surface single package card rather than destination cards
    pass

elif intent.specificity in ("exploratory", "directional"):
    # hotel price optional
    # surface destination cards with indicative flight price
    pass
```

---

## 7. Stage 5 — Explanation

**Owner:** Person 1  
**Input:** top-k RankedCandidates + IntentStruct  
**Output:** same list with explanation field populated  
**Model:** claude-sonnet-4-20250514  
**Latency target:** < 2s  

### 7.1 Explanation prompt

```
You are writing one-line explanations for travel recommendations.
Each explanation must reference the user's own words and vibe tags — 
do not write generic destination copy.

User vibe: {vibe_tags}
User budget: {budget or "not specified"}

For each destination below, write one sentence explaining why it matches the vibe.
Reference specific vibe tags. Be direct. Maximum 20 words per explanation.

Destinations:
{ranked_candidates_json}

Return JSON array: [{ "place": string, "explanation": string }]
```

### 7.2 Example output

```json
[
  {
    "place": "Dolomites",
    "explanation": "Matches your rural and quiet preference — remote valleys with very low tourist density."
  },
  {
    "place": "Aosta Valley",
    "explanation": "Off-beaten-path Alpine countryside with nature trails — fits your niche, nature vibe."
  }
]
```

---

## 8. Session management

**Owner:** Person 4  
**Storage:** in-memory dict (sufficient for hackathon)  

### 8.1 Session schema

```python
class Session:
    session_id: str
    created_at: datetime
    intent: IntentStruct
    candidates: list[RankedCandidate]
    turn_history: list[str]   # raw user messages in order
```

### 8.2 API endpoints

```
POST /session/start
Body: { "query": string, "origin": string, "market": string, "locale": string }
Response: { "session_id": string, "intent": IntentStruct, "results": list[RankedCandidate] }

POST /session/refine
Body: { "session_id": string, "message": string }
Response: { "intent": IntentStruct, "diff": dict, "results": list[RankedCandidate] }

GET /session/{id}/months/{hub_entity_id}
Response: { "months": list[MonthPrice] }

GET /session/{id}/state
Response: { "intent": IntentStruct, "results": list[RankedCandidate], "history": list[str] }
```

### 8.3 Orchestration flow

```python
async def handle_start(query, origin, market, locale):
    culture = get_culture(market, locale)           # Person 2
    intent  = extract_intent(query)                 # Person 1
    hubs    = resolve_hubs(intent.places)           # Person 2
    prices  = get_indicative_prices(origin, hubs)   # Person 2 — parallel
    scores  = score_all(intent.places, intent.vibe) # Person 3 — uses pre-stored data
    ranked  = rank(merge(hubs, prices, scores), intent)  # Person 3
    results = explain(ranked[:5], intent)           # Person 1
    session = store_session(intent, results)
    return session

async def handle_refine(session_id, message):
    session = load_session(session_id)
    diff    = diff_intent(session.intent, message)  # Person 1
    intent  = apply_diff(session.intent, diff)
    # re-run from stage 2 if places or countries changed
    # re-run from stage 4 if only budget or crowd_pref changed
    ...
```

### 8.4 Re-run optimisation

Not all refinements require a full pipeline re-run:

| Changed fields | Re-run from |
|---|---|
| places, countries | Stage 2 (new API calls needed) |
| vibe | Stage 3 (re-score existing candidates) |
| budget | Stage 4 (re-rank only) |
| start_date, end_date | Stage 2 (new date range for API calls) |
| direct_only | Stage 2 (re-query with nonstop param) |

---

## 9. Offline embedding pipeline

**Owner:** Person 3  
**Run:** before the demo, output committed to repo  

### 9.1 Destination corpus

Fixed list of ~40 destinations covering the three use cases:

- UC1 alps destinations: Ötztal Valley, Stubai Valley, Dolomites, Aosta Valley, Triglav foothills, Soča Valley, Bernese Oberland, Gruyères
- UC2 Slovenia: Ljubljana, Lake Bled, Piran, Maribor
- UC3 warm/flexible: Marrakech, Lisbon, Seville, Algarve, Crete, Sardinia, Malta, Tbilisi, Kotor, Plovdiv

For each: fetch hotel reviews via Hotels Reviews API, run offline pipeline (section 5.1), store output.

### 9.2 Embedding model

`text-embedding-3-small` (OpenAI) or `all-MiniLM-L6-v2` (local, no API cost).

For the hackathon, all-MiniLM-L6-v2 is preferred — runs locally, no API key needed for embeddings, fast inference, output is 384-dimensional float32 vectors.

---

## 10. Technology choices

| Component | Choice | Reason |
|---|---|---|
| LLM | Claude Sonnet or GPT-4o | JSON output reliability |
| Sentiment analysis | VADER | Rule-based, no model loading, handles negation |
| Embedding model | all-MiniLM-L6-v2 | Local, fast, no API cost |
| Vector storage | Flat JSON + numpy dot product | Sufficient for 40-destination corpus |
| Server | FastAPI (Python) | Async support, fast to write |
| Session storage | In-memory dict | Sufficient for hackathon |

---

## 11. Integration sequence

Recommended order for integration day:

1. Person 4 starts server with stub endpoints returning mocked data
2. Person 2 replaces stubs with real Skyscanner API calls — test with UC2 (simplest query)
3. Person 1 replaces mocked intent with real LLM extraction — test with UC1 input
4. Person 3 confirms offline embeddings are built — plug scoring into server
5. Full end-to-end test: UC1 → UC2 → UC3 in order
6. Frontend connects to `/session/start` and `/session/refine`
