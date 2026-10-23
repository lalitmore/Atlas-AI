# Atlas AI

**Live demo → [atlasai-iota.vercel.app](https://atlasai-iota.vercel.app)**

A multi-agent travel planning app built on Google's Agent Development Kit (ADK 2.3+) and Gemini. Describe a trip in plain language — Atlas researches it, optimizes the route, and writes a day-by-day itinerary with booking links, transport guidance, an interactive map, and PDF export.

**Current defaults:** Intake and both research agents use `gemini-3.5-flash-lite`;
the itinerary writer uses `gemini-3.6-flash`.
Live Google Search grounding is enabled by default and uses your configured
Gemini Developer API project. API usage can incur charges, including
when Atlas runs locally. Set `ENABLE_SEARCH_GROUNDING=FALSE` only when deliberately
creating general-knowledge drafts without live research.

---

## What it does

You describe a trip the way you'd text a friend:

> *"10 days in Japan in October, me and my vegetarian girlfriend, we love anime, food, nature, and photography, budget around $4,500, and we hate early mornings"*

Atlas turns that into a fully structured, grounded, route-optimized itinerary in ~40–60 seconds — with named restaurants, real transport advice, and links to book hotels, flights, and navigate every leg.

---

## Architecture

Atlas is an orchestrated pipeline of specialized agents, not a single prompted model.

```
Free-text input
      │
      ▼
┌─────────────────┐
│  Intake Agent   │  Structures the request into a typed TripBrief
│  (Flash-Lite)   │  (destination, party size, interests, dietary needs,
└────────┬────────┘   assumptions, missing info)
         │
         ▼
┌──────────────────────┐
│ Grounded Research    │  Live web research via Google Search grounding —
│ Agent (Flash-Lite)   │  real festival dates, prices, named restaurants
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Structured Research  │  Turns findings into typed DestinationResearch
│ Agent (Flash-Lite)   │  (candidate areas with lat/lng, matched interests)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Route Optimizer     │  Pure Python — NOT an LLM. Haversine distances →
│  (ADK callback)      │  nearest-neighbor seed → 2-opt TSP improvement →
└──────────┬───────────┘  day allocation. Deterministic route heuristic.
           │
           ▼
┌──────────────────────┐
│  Itinerary Agent     │  Writes the day-by-day plan against the fixed route.
│  (Flash — full)      │  Typed schemas (FoodStop, CityTransport) with required
└──────────┬───────────┘  fields force real, committed specifics.
           │
           ▼
   Streamed to the UI
   (5 live stages via SSE)
```

### Key engineering decisions

**Deterministic routing instead of asking the model.** Route order is computed with a nearest-neighbor and 2-opt TSP heuristic that reduces backtracking without a model call. The itinerary writer follows this route and its day allocations; the heuristic does not guarantee a globally optimal tour.

**Schema as a quality-control mechanism.** `FoodStop` requires a name and meal label, and the writer is instructed to use researched venues with suitable dietary options. The schema enforces structure; it cannot establish that a venue exists or that every generated detail is correct.

**Grounding for freshness.** Festival dates, prices, and restaurants come from live Google Search, not training data. The research agent is where "real world, right now" enters.

**Two research agents because Gemini requires it.** Gemini rejects `output_schema` combined with `google_search` in one call. Grounding and structuring are cleanly split — a constraint that produced better separation of concerns anyway.

**Hybrid model tiering.** Intake and both research agents use `DEFAULT_MODEL`
(default `gemini-3.5-flash-lite`); the itinerary writer alone uses `ITINERARY_MODEL`
(default `gemini-3.6-flash`) for stronger itinerary reasoning. Each setting can be
overridden independently. There is no automatic model fallback.
For local use, verify both model IDs with your key before planning. If access to
`gemini-3.6-flash` cannot be confirmed, set
`ITINERARY_MODEL=gemini-3.5-flash-lite` in the local pipeline `.env` until it can.

**Streaming as UX honesty.** Research takes ~30–40 seconds. Instead of a blank screen, five named stages stream live via SSE — the latency becomes a feature that shows the work.

**Deep links over fake booking.** Every output links to a real site (Google Maps, Google Flights, Booking.com) pre-filled with the trip's context. Atlas plans; real services book. No simulated inventory.

---

## Stack

| Layer | Technology |
|---|---|
| Agent framework | Google ADK 2.3+ |
| Intake, grounded research, structured research | `gemini-3.5-flash-lite` (`DEFAULT_MODEL`) |
| Itinerary writer | `gemini-3.6-flash` (`ITINERARY_MODEL`) |
| Grounding | Google Search (enabled by default; `ENABLE_SEARCH_GROUNDING`) |
| Backend | FastAPI, sse-starlette, Pydantic |
| Optimization | Pure Python (haversine + 2-opt TSP) |
| Frontend | Next.js 16, React 19, Tailwind v4, TypeScript |
| Map | react-leaflet v5, OpenStreetMap standard tiles |
| Backend deploy | Docker → Google Cloud Run |
| Frontend deploy | Vercel |

---

## Features

- **Single free-text input** — no forms, no dropdowns; plain language is the UX
- **Live agent pipeline** — departures-board UI streams all 5 stages in real time
- **Interactive route map** — numbered pins, dashed polyline, auto-fit bounds
- **Named, linked restaurants** — researched dining suggestions with dietary notes; each links to a Maps search
- **Download PDF** — exports the completed plan, original request, assumptions, route, daily activities, food, transport, open items, and clickable booking/navigation links; slugged filenames and bundled Japanese/Korean fonts. Exporting an existing result makes no Gemini call.
- **Transport guidance** — per-city "getting here" and "getting around" advice; inter-city mode recommendation
- **Booking deep links** — Directions (all modes), Hotels, Flights, vegetarian-food search per city
- **Honest output** — explicit assumptions, open items, and live links as the verification layer
- **Abuse guardrails** — input cap, per-IP rate limiting, global daily cap, concurrency control

---

## Project structure

```
Atlas AI/
├── backend/
│   ├── atlas/
│   │   ├── agents/
│   │   │   ├── intake/
│   │   │   ├── research/          # grounded + structured agents
│   │   │   ├── itinerary/
│   │   │   └── pipeline/          # SequentialAgent root + .env
│   │   ├── api/
│   │   │   ├── main.py            # FastAPI app + SSE streaming
│   │   │   └── guardrails.py      # abuse protection
│   │   ├── optimization/
│   │   │   └── route.py           # haversine + 2-opt TSP
│   │   └── schemas/               # Pydantic output schemas
│   ├── Dockerfile
│   └── pyproject.toml
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx           # main UI (departures board)
        │   ├── layout.tsx
        │   └── globals.css        # Tailwind v4 design tokens
        ├── components/
        │   ├── RouteMap.tsx       # Leaflet + OpenStreetMap tiles
        │   ├── DownloadPdfButton.tsx
        │   └── ItineraryPdf.tsx   # lazy-loaded PDF document
        └── lib/
            ├── atlas.ts           # types + SSE stream parser
            └── links.ts           # deep-link URL builders
```

---

## Running locally

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Copy the template without overwriting an existing local file, then edit its key.
cp -n .env.example atlas/agents/pipeline/.env
# Set GOOGLE_API_KEY in atlas/agents/pipeline/.env; never commit that file.

env -u GOOGLE_API_KEY -u GEMINI_API_KEY uvicorn atlas.api.main:app --reload --port 8000
```

The local command clears inherited key variables for that process so uvicorn uses
the key in `atlas/agents/pipeline/.env`. Otherwise, environment variables take
precedence over that file and may select a different Gemini project's quota.

**Frontend**

```bash
cd frontend
npm ci
npm run dev -- --hostname localhost     # → http://localhost:3000 (this Mac only)
```

The frontend reads `NEXT_PUBLIC_API_BASE` for the backend URL (defaults to `http://localhost:8000`).

Use a valid Gemini Developer API key with access and quota for the configured models
and Search grounding. Local hosting does not make Gemini API requests free. No cloud
deployment is needed for local use.

Settings in `atlas/agents/pipeline/.env` (or Cloud Run environment variables):

```dotenv
DEFAULT_MODEL=gemini-3.5-flash-lite
ITINERARY_MODEL=gemini-3.6-flash
ENABLE_SEARCH_GROUNDING=TRUE
```

Production must keep Search grounding enabled. Google documents this model ID,
structured outputs, and Search support in its
[model reference](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).
See [pricing](https://ai.google.dev/gemini-api/docs/pricing) for billed API usage.
The original code used `gemini-2.5-flash-lite` for intake/research/structuring and
`gemini-2.5-flash` for the itinerary. Those were changed after Google rejected the
old Flash-Lite model. Hybrid tiering is retained with the supported 3.x models.
The itinerary model ID is documented in Google's [Gemini 3.6 Flash reference](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash).

## Offline checks

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/ruff check atlas tests
cd ../frontend
node --test tests/*.test.mjs
npm run lint
npx tsc --noEmit
npm run build
```

Backend tests use dummy credentials and mocked provider responses; they do not call
Gemini. The frontend build may fetch Google Fonts. PDF rendering can be checked
without generating a new trip:

```bash
cd frontend
node tests/render-itinerary-pdf.mjs tests/fixtures/japan.json ../output/pdf/sample.pdf
```

See [request-role/model evidence](docs/hybrid-model-evidence.md), the
[fixture PDF link audit](docs/pdf-link-audit.md), and the dated
[local verification report](docs/home-wifi-verification.md). Generated PDFs,
screenshots, logs, dependencies, caches, and real dotenv files stay out of Git.

---

## Deployment

- **Backend:** Dockerized FastAPI on Google Cloud Run (`--max-instances 1`, `--no-cpu-throttling`, `--min-instances 1`)
- **Frontend:** Vercel (`vercel --prod` from `frontend/`)
- **API key:** Gemini Developer API, Tier 1 with billing enabled; Search grounding ON.
- **CORS:** `ALLOWED_ORIGINS` env var on Cloud Run, set to the Vercel production domain

Cloud Run environment for the production Developer API backend:

| Variable | Value |
| --- | --- |
| `GOOGLE_API_KEY` | Tier 1 key, preferably a secret reference |
| `GOOGLE_GENAI_USE_VERTEXAI` | `false` |
| `GOOGLE_GENAI_USE_ENTERPRISE` | Unset or `false` |
| `DEFAULT_MODEL` | `gemini-3.5-flash-lite` |
| `ITINERARY_MODEL` | `gemini-3.6-flash` |
| `ENABLE_SEARCH_GROUNDING` | `true` |
| `ALLOWED_ORIGINS` | `https://atlasai-iota.vercel.app` |

---

## How this differs from asking ChatGPT or Gemini directly

Asking a model directly gives one LLM doing everything in a single shot: guessing route order, potentially making up restaurant names, no guaranteed live data, and a black-box wait until the answer arrives.

Atlas adds the orchestration layer that makes the output reliable and actionable:

- **Real route math** — a deterministic optimizer, not a model guessing geography
- **Grounded, current facts** — live search for real dates, prices, and named places
- **Enforced structure** — typed schemas that make vague filler structurally impossible
- **Transparency** — five distinct agent stages streaming live
- **Actionability** — every output deep-links to a live booking or navigation flow

Gemini is the engine inside Atlas. Atlas is the system around it.

---
