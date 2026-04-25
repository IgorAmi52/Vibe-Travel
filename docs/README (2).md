# Skyscanner Hackathon — Intent-Driven Travel Discovery

**Track:** Be the Future of Travel  
**Team size:** 4  
**Theme:** AI-powered travel experience that understands traveller intent, cuts through complexity, and helps people make confident, informed decisions.

---

## What we are building

A session-based travel discovery feature that replaces the traditional search form with natural language input. The user describes what they want — a vibe, a region, a rough budget — and the system returns ranked destination and hotel recommendations grounded in live Skyscanner pricing data, with human-readable explanations tied directly to what the user asked for.

The key differentiator from Skyscanner's existing Savvy Search is a persistent intent session: the user's parsed preferences are shown as removable tags, and every refinement turn updates those preferences rather than starting over. Recommendations are ranked by a combination of semantic hotel matching, keyword-sentiment scoring, and live flight pricing — not by an LLM prompt alone.

---

## Demo use cases

### UC1 — Vague exploratory with refinement
> "niche countryside in the alps"

Full pipeline demo. Intent extracted, places and countries generated, flights retrieved, hotels scored. User refines mid-session:
> "narrow it down to north of Italy"

Intent struct is diffed, not reset. New candidates returned scoped to Dolomites and Aosta Valley. Ends with cheapest month view for top result.

### UC2 — Directional with budget
> "weekend in Slovenia, budget €300 total"

Specificity classifier routes to package view. Flights + hotel combined cost checked against budget. User refines:
> "direct flights only"

Shallow link on confirmed card hands off to live Skyscanner search.

### UC3 — Seasonal, open dates
> "somewhere warm, I'm flexible on when"

Fully flexible date query. Date aggregation API finds cheapest month per candidate. Crowd signal used in re-ranking. System surfaces the best time to go as part of the recommendation.

---

## Team split

| Person | Responsibility |
|---|---|
| 1 | Intent & LLM layer |
| 2 | Skyscanner API client |
| 3 | Aggregation & ranking |
| 4 | API server & session management |

Frontend handled separately after core pipeline is proven.

---

## Repo structure

```
/intent          # Person 1 — LLM prompts, intent extraction, explanation
/skyscanner      # Person 2 — API client wrappers
/ranking         # Person 3 — scoring, hotel matching, aggregation
/server          # Person 4 — FastAPI server, session store, orchestration
/embeddings      # Pre-built offline artefacts — stored vectors, keyword dict
/docs            # PRD.md, ARD.md, this file
```

---

## Shared types

All four modules depend on these two types. Agree on them before splitting.

```python
class IntentStruct:
    places: list[str]        # LLM-generated specific places
    countries: list[str]     # corresponding countries (metadata)
    start_date: str | None
    end_date: str | None
    budget: int | None
    vibe: list[str]          # destination + accommodation character
    specificity: str         # "exploratory" | "directional" | "specific"

class RankedCandidate:
    place: str               # display name e.g. "Dolomites"
    hub_city: str            # nearest airport city e.g. "Venice"
    hub_entity_id: str       # Skyscanner entity ID
    country: str
    indicative_flight_price: float
    hotel_match_score: float
    indicative_hotel_price: float | None
    combined_score: float
    cheapest_month: str | None
    shallow_link: str | None
    explanation: str | None
```

---

## APIs used

| API | Purpose |
|---|---|
| Skyscanner Autosuggest | Place names → entity IDs |
| Flights Indicative (anywhere) | Candidate country generation |
| Flights Indicative (destination city) | Hub city prices per country |
| Flights Indicative (by month) | Cheapest month per route |
| Flights Indicative (by date) | Day-level calendar for UC1 refinement |
| Flights Live Prices | UC2 handoff to bookable results |
| Hotels Indicative | UC2 combined cost check |
| Culture API | Market / locale / currency resolution |
| Shallow Link Generator | "Search on Skyscanner" CTA on cards |

---

## What we are not building

- Car hire
- Multi-city routing
- User accounts or persistent history
- Hotels Live Prices (indicative sufficient for demo)
- Carriers API (raw carrier codes acceptable for demo)
