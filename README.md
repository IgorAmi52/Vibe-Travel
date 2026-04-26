# Vibe Travel

AI-powered trip planner. Type a free-form request ("Alps ski trip, 7 days, budget 2500, for two") and get back ranked flight + hotel combinations matched to your vibe.

## How it works

The backend extracts a structured travel intent from your query with Gemini, fans out across every candidate destination to search flights on Skyscanner, fetches Booking.com hotels for those destinations, and ranks hotels by embedding similarity between your vibe description and each property's description, amenities, and reviews. The frontend presents the results as grouped trip option cards with deep links straight into Skyscanner and Booking.com pre-filled with your dates and traveller count.

## Structure

| Directory | Stack | Purpose |
|-----------|-------|---------|
| [`back/`](back/README.md) | Python 3.11, LangGraph, Gemini, stdlib HTTP server | Intent extraction, flight search, hotel ranking, HTTP API |
| [`frontend/`](frontend/README.md) | Next.js 15, React 19, TypeScript, Tailwind | Chat-style UI, package cards, Next.js route handler proxy to the backend |

## Docs

- [`PRD.md`](PRD.md) — Product requirements, use cases, FRs and NFRs
- [`back/architecture/ARCHITECTURE.md`](back/architecture/ARCHITECTURE.md) — Pipeline diagram and module map
- [`back/API_CONTRACT.md`](back/API_CONTRACT.md) — HTTP endpoints and JSON schemas

## Quick start

**Backend** — see [`back/README.md`](back/README.md) for the full setup:

```bash
cd back
cp .env.example .env   # add API keys, or leave TRIP_PLANNER_MODE=mock
pip install -U -r requirements.txt
python3 main.py serve --host 127.0.0.1 --port 8080
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```

The frontend talks to the backend through `frontend/app/api/invoke/route.ts`, which proxies to `http://127.0.0.1:8080/invoke` by default. Override with the `BACKEND_API_URL` env var if your backend runs elsewhere.
