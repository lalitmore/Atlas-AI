# Atlas AI

**Live demo → [atlasai-iota.vercel.app](https://atlasai-iota.vercel.app)**

A multi-agent travel planning app built on Google's Agent Development Kit (ADK 2.0) and Gemini. Describe a trip in plain language — Atlas researches it, optimizes the route, and writes a day-by-day itinerary with booking links, transport guidance, and an interactive map.

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
└──────────┬───────────┘  day allocation. Deterministic, correct every time.
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

**Deterministic routing instead of asking the model.** LLMs are unreliable at exact combinatorial optimization. Route order is computed with a 2-opt TSP solver — reliable, free, and correct every time. The model only writes prose against a mathematically optimal skeleton.

**Schema as a quality-control mechanism.** A required `name` field on `FoodStop` makes "quick veg meal in Arashiyama" structurally impossible. The model is forced to commit to a real, named place. Quality enforced by the data contract, not just prompt wording.

**Grounding for freshness.** Festival dates, prices, and restaurants come from live Google Search, not training data. The research agent is where "real world, right now" enters.

**Two research agents because Gemini requires it.** Gemini rejects `output_schema` combined with `google_search` in one call. Grounding and structuring are cleanly split — a constraint that produced better separation of concerns anyway.

**Hybrid model tiering.** Cheap Gemini 2.5 Flash-Lite for intake/research/structuring; full Gemini 2.5 Flash only for the itinerary writer where date ordering and reasoning matter. Explicit cost/quality tradeoff.

**Streaming as UX honesty.** Research takes ~30–40 seconds. Instead of a blank screen, five named stages stream live via SSE — the latency becomes a feature that shows the work.

**Deep links over fake booking.** Every output links to a real site (Google Maps, Google Flights, Booking.com) pre-filled with the trip's context. Atlas plans; real services book. No simulated inventory.

---

## Stack

| Layer | Technology |
|---|---|
| Agent framework | Google ADK 2.0 |
| Models | Gemini 2.5 Flash + Flash-Lite |
| Grounding | Google Search (ADK built-in) |
| Backend | FastAPI, sse-starlette, Pydantic |
| Optimization | Pure Python (haversine + 2-opt TSP) |
| Frontend | Next.js 16, React 19, Tailwind v4, TypeScript |
| Map | react-leaflet v5, Carto basemap tiles |
| Backend deploy | Docker → Google Cloud Run |
| Frontend deploy | Vercel |

---

## Features

- **Single free-text input** — no forms, no dropdowns; plain language is the UX
- **Live agent pipeline** — departures-board UI streams all 5 stages in real time
- **Interactive route map** — numbered pins, dashed polyline, auto-fit bounds
- **Named, linked restaurants** — `FoodStop` schema forces real place names; each links to a live Maps search
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
        │   └── RouteMap.tsx       # Leaflet map component
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

# add your key to atlas/agents/pipeline/.env
echo "GOOGLE_API_KEY=your_key_here" > atlas/agents/pipeline/.env
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> atlas/agents/pipeline/.env

uvicorn atlas.api.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev     # → http://localhost:3000
```

The frontend reads `NEXT_PUBLIC_API_BASE` for the backend URL (defaults to `http://localhost:8000`).

---

## Deployment

- **Backend:** Dockerized FastAPI on Google Cloud Run (`--max-instances 1`, `--no-cpu-throttling`, `--min-instances 1`)
- **Frontend:** Vercel (`vercel --prod` from `frontend/`)
- **API key:** Gemini Developer API, Tier 1 (billing enabled on the AI Studio project)
- **CORS:** `ALLOWED_ORIGINS` env var on Cloud Run, set to the Vercel production domain

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

*Built as a portfolio project targeting Google AI/Cloud engineering roles. Stack chosen to showcase Google ADK, Gemini structured output, grounding, Cloud Run, and full-stack AI product design.*
