# Vibe Travel — Frontend

Next.js 15 + React 19 + TypeScript + Tailwind UI for the Vibe Travel trip planner. The frontend is a thin chat-style interface around the backend graph: it sends the user's free-form query (and any clarification turns) to the Python backend and renders the returned flight + hotel packages.

## Prerequisites

- Node.js 18.18+ (Next.js 15 requirement)
- The backend running locally on `http://127.0.0.1:8080` — see [`../back/README.md`](../back/README.md)

## Setup

```bash
npm install
npm run dev          # http://localhost:3000
```

To point at a non-default backend:

```bash
BACKEND_API_URL=http://localhost:9090 npm run dev
```

## Scripts

| Command | What it does |
|---------|--------------|
| `npm run dev` | Start the Next.js dev server |
| `npm run dev:turbo` | Same, with Turbopack |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint (Next.js config) |

## Architecture

The frontend is intentionally simple: there is no client-side store, no auth, and no persistence. State lives in React on the page; every refinement (clarification turn) re-submits the previous backend `state` so the pipeline can apply the new query on top of it.

```
app/page.tsx
   │
   ▼
PackagesExperience  ── owns the chat session state
   │
   ├─ SearchSummaryBar       (query input + traveller count + clarification chips)
   ├─ ResultsLayout
   │     ├─ ResultsLoadingState  (skeleton while a request is in flight)
   │     └─ PackageCard[]        (one per destination group)
   └─ AppChrome              (header / branding)
```

### Key files

| Path | Purpose |
|------|---------|
| `app/page.tsx` | Entry page; mounts `PackagesExperience` |
| `app/api/invoke/route.ts` | Server-side Next.js route handler that proxies `POST /api/invoke` → backend `POST /invoke` |
| `lib/sessionClient.ts` | Browser-side fetch wrapper that calls `/api/invoke` and threads `state` across turns |
| `lib/mapInvokeResponse.ts` | Converts the backend `InvokeResponse` into a `SessionSnapshot` (intent chips, package view models, clarification prompts). Builds the Skyscanner and Booking.com deal URLs |
| `lib/mapPackageView.ts` | Shapes a single package (flights + hotel) into the props the card expects |
| `lib/types.ts` | Shared TypeScript types for the backend contract and view models |
| `lib/formatMoney.ts` | Currency formatting helper |
| `lib/mock/` | Static fixtures used as a fallback when the backend is unreachable |
| `components/PackageCard.tsx` | One destination's flight options + featured hotel + deal CTAs |
| `components/PackagesExperience.tsx` | Orchestrates queries, clarification turns, and result display |
| `components/SearchSummaryBar.tsx` | Search input + intent chips (removable) |
| `components/ResultsLayout.tsx` | Layout shell for the packages grid |
| `components/ResultsLoadingState.tsx` | Skeleton state |
| `components/AppChrome.tsx` | Header / branding (VibeTravel) |
| `components/FilterSidebar.tsx` | Filter controls (currently hidden in the layout) |

### Deal links

`lib/mapInvokeResponse.ts` is responsible for building the outbound URLs the user clicks:

- **Skyscanner flights** — uses `adultsv2`, `children=0`, `infants=0`, `cabinclass=economy`, and `rtn=1`/`rtn=0` so the Skyscanner search page opens with the correct traveller count and trip type already selected.
- **Booking.com hotels** — uses `dest_type=hotel&dest_id=<hotel_id>` with `checkin`/`checkout` so the link deep-links straight to the property page on the right dates instead of doing a fuzzy text search. Falls back to flight dates when the user did not specify trip dates.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_API_URL` | `http://127.0.0.1:8080` | Where the `/api/invoke` route handler proxies to |

## Production

```bash
npm run build
npm run start
```

Deploy anywhere that runs Node.js. Make sure `BACKEND_API_URL` points at the deployed backend.
