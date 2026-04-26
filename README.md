# Vibe Travel

AI-powered trip planner. Type a free-form request ("Alps ski trip, 7 days, budget 2500") and get back ranked flight + hotel combinations matched to your vibe.

## How it works

The backend extracts structured travel intent from your query using Gemini, searches Skyscanner for flights and Booking.com for hotels, and ranks hotels by embedding similarity between your vibe description and hotel content (description, amenities, reviews). The frontend presents the results as grouped trip options.

## Structure

| Directory | Stack | Purpose |
|-----------|-------|---------|
| [`back/`](back/README.md) | Python, LangGraph, Gemini | Intent extraction, flight search, hotel ranking, HTTP API |
| `frontend/` | Next.js, TypeScript, Tailwind | Chat-style UI, trip results display |

## Docs

- [`PRD.md`](PRD.md) — Product requirements, use cases, FRs and NFRs

## Quick start

**Backend** — see [`back/README.md`](back/README.md) for full setup:

```bash
cd back
cp .env.example .env   # add API keys
pip install -U -r requirements.txt
python3 main.py serve --host 127.0.0.1 --port 8080
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
```
