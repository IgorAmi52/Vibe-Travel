# PRD — Vibe Travel
**Version:** 0.2  
**Status:** Draft  

---

## 1. Problem

Traditional flight and hotel search requires the user to already know what they want — origin, destination, dates. This works for high-intent bookings but fails exploratory travellers: people who have a feeling about a trip but not a specific plan.

Existing natural language tools (e.g. Skyscanner Savvy Search) generate suggestions from an LLM with no grounding in live prices, no session memory, and no path from "interesting idea" to "booking decision." The user gets a list, not a conversation.

---

## 2. Solution

Vibe Travel is a session-based, intent-driven trip discovery experience. The user describes a trip in plain language — a mood, a season, a feeling — and the system finds real flights and hotels that match.

**The core idea: vibe as a search signal.**  
Instead of filtering by destination and dates, the system extracts a structured *intent* (places, dates, budget, vibe keywords) from the user's message and uses the vibe to semantically rank hotels. Hotel descriptions, amenities, and guest reviews are embedded using a language model; the user's vibe is embedded the same way; cosine similarity scores each hotel against what the user actually meant. Price and guest rating combine into a final composite score.

This means a query like *"quiet mountain escape, nothing too touristy"* returns hotels ranked by how well they actually match that feeling — not by proximity to a keyword.

The experience is conversational: the system shows what it understood, lets the user correct it, and progressively refines results without losing session context.

---

## 3. Users

| Segment | Description |
|---------|-------------|
| **Exploratory** | Knows the kind of trip they want, not the destination. Browsing 4–12 weeks out. |
| **Directional** | Has a destination in mind, wants to validate it against budget and find accommodation. |

---

## 4. Use Cases

### UC1 — Vague exploratory, mid-session refinement
> *"niche countryside in the alps"*

1. System extracts: `places = [Ötztal, Dolomites, Aosta Valley]`, `vibe = "rural off-beaten-path quiet"`
2. Intent tags shown — user sees what was understood
3. Flights (Skyscanner indicative) and hotels (vibe-ranked) fetched per place
4. Result cards shown with place, indicative price, and one-line vibe explanation
5. User refines: *"narrow to north Italy"* → intent diffed, results update in-session

### UC2 — Directional with budget constraint
> *"weekend in Slovenia, budget €300 total"*

1. System extracts: `places = [Ljubljana, Lake Bled]`, `budget = 300`
2. Flight + hotel combined cost checked against budget
3. Package card shown: within-budget options highlighted, over-budget shown ranked lower
4. User refines: *"direct flights only"* → `direct_only` flag added, results update
5. CTA: shallow link opens Skyscanner live search pre-filled with parameters

### UC3 — Open destination, flexible dates
> *"somewhere warm, I'm flexible on when"*

1. System extracts: `vibe = "warm relaxed"`, `dates = null`
2. Indicative-by-month called for top candidates — cheapest month found per destination
3. Cards shown with best-time signal: *"Marrakech — April, from €89"*
4. User refines: *"least touristy"* → vibe re-ranked with crowd-preference signal

---

## 5. Functional Requirements

### FR1 — Intent Extraction
- Accept free-text input of any length
- Extract: `places`, `countries`, `start_date`, `end_date`, `budget`, `vibe`, `person_count`
- Places must reflect the vibe — a skiing query returns ski resorts, not cities
- Support two modes: `mock` (rule-based, no API) and `gemini` (structured LLM output)

### FR2 — Session & Clarification
- Each session persists `IntentStruct` and result set across turns
- If intent is incomplete, system halts and returns a `clarification_prompt`
- Clarification re-enters the pipeline with the prior state; `iteration` increments per turn
- Intent tags shown as removable chips; removing a tag triggers a result refresh

### FR3 — Flight Search
- Resolve each candidate place to a Skyscanner entity ID via autosuggest
- Fan out across every resolved place so multi-destination queries (e.g. "Alps") return options for several airports, not just the first match
- Retrieve roundtrip flight chains (Skyscanner indicative + live prices): departure + return legs, price, duration
- Support indicative (destination-open) and chains (roundtrip) modes; cap indicative trip length at 30 days when the user has not provided dates
- Scale per-person Skyscanner prices to the requested traveller count
- Places with no flight data are reported back as a clarification prompt rather than silently dropped

### FR4 — Hotel Search & Vibe Ranking
- Fetch hotels for each destination (Booking.com via RapidAPI)
- Resolve destinations against `city`, `region`, `district`, `landmark`, and `country` autosuggest types so region-level queries (e.g. "Dolomites") still find inventory
- Drop properties with no availability for the requested dates so deal links never land on a "no rooms" page
- For each remaining hotel, build an embeddable text blob: description + amenities + top review texts
- Embed the blob and the user's vibe string using Gemini (`gemini-embedding-001`)
- Score each hotel:
  ```
  composite_score = 0.7 × vibe_similarity + 0.2 × price_score + 0.1 × guest_rating
  ```
- Return hotels sorted by composite score; weights configurable via env

### FR5 — Result Grouping & Explanation
- Group results as flight + hotel pairs per destination
- Every result card must include a one-line explanation referencing the user's own vibe tags
- Explanation generated by the LLM using `IntentStruct` as context — no generic copy

### FR6 — Booking Handoff
- Every result card must have a shallow-link CTA
- Skyscanner flight links pre-fill origin, destination, both legs' dates, and traveller count (`adultsv2`)
- Booking.com hotel links deep-link to the specific property (`dest_type=hotel&dest_id=<hotel_id>`) and pre-fill check-in / check-out dates
- When the user did not specify trip dates, the deal links fall back to dates from the matched flight quote so the booking pages always open on a valid window

### FR7 — HTTP API
- Expose `/invoke` (trip planner), `/flights/chains`, `/flights/indicative`, `/health`, `/schema`
- `POST /invoke` accepts `NEW` and `CLARIFICATION` request types
- All endpoints return JSON; error codes: `400` bad request, `404` unknown route, `500` internal
- The frontend reaches the backend through a thin Next.js route handler (`/api/invoke`) so the browser never talks to the Python service directly

---

## 6. Non-Functional Requirements

### NFR1 — Performance
- Intent extraction must complete in under 3 seconds (p95)
- Full pipeline (intent + flights + hotels) must complete in under 10 seconds for a typical query
- Hotel embedding computed on-the-fly per request; migrate to vector DB at scale

### NFR2 — Reliability
- All external API calls use exponential backoff with configurable retries and timeouts
- Pipeline failures surface as structured errors in the response, not crashes

### NFR3 — Configurability
- API keys, model names, timeouts, retries, and scoring weights all driven by `.env`
- `mock` mode must run without any external API keys for local development and testing

### NFR4 — Observability
- Structured logs at INFO level to console and rotating file (`logs/trip_planner.log`)
- Each pipeline run logs intent, node transitions, and external API call outcomes

### NFR5 — Extensibility
- New pipeline nodes added via `core/nodes/` with no changes to existing nodes
- New inference backends implement `IntentInferenceClient` interface and wire into `core/app.py`
- New API clients use `ApiConnector` for consistent retry and timeout behaviour

---

## 7. Out of Scope

- User authentication or persistent cross-session history
- Multi-city routing or car hire
- Hotels live pricing (indicative is sufficient for the demo)
- Group trip coordination
- Native mobile app
- Carrier name resolution (entity codes acceptable)

---

## 8. Success Metrics

For the hackathon demo, success is qualitative:

| Check | Criteria |
|-------|---------|
| All three use case happy paths complete end-to-end without manual intervention | UC1, UC2, UC3 |
| Intent tags correctly reflect typed input | All inputs |
| Refinement turns update results visibly and correctly | UC1, UC2 |
| At least one result per use case explains a specific vibe tag from the input | All UCs |
| UC2 shallow link opens a valid Skyscanner search page | UC2 |

---

## 9. Open Questions

| Question | Priority |
|---------|---------|
| Can we get MCP server access from Skyscanner at the hackathon? | High |
| What hotel corpus do we pre-embed — fixed list of destinations for the demo? | High |
| How do we handle places with no Hotels Indicative coverage? | Medium |
| Map view on result cards, or list only? | Low |
