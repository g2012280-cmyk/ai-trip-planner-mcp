# Trip Planner

An AI-powered travel itinerary generator for cities across China. Enter a destination, travel dates, and preferences — the app returns a day-by-day plan with attractions, meals, hotels, weather, and a cost breakdown.

## Architecture

```
  User request
       │
       ▼
┌─────────────────────────────────────────┐
│         Orchestration Layer             │
│                                         │
│  DeepSeek LLM  ·  4 specialised agents  │
│                                         │
│  Understands intent, decomposes tasks,  │
│  and assembles the final itinerary      │
└──────────┬──────────────────────────────┘
           │ needs real-world data
           ▼
┌─────────────────────────────────────────┐
│            Tooling Layer                │
│                                         │
│  Amap MCP Server  (@amap/amap-maps-*)   │
│                                         │
│  Live POI search · weather · geocoding  │
└──────────┬──────────────────────────────┘
           │ raw LLM output
           ▼
┌─────────────────────────────────────────┐
│          Validation Layer               │
│                                         │
│  Pydantic v2 schemas                    │
│                                         │
│  Enforces types, rejects bad output,    │
│  guarantees the frontend gets clean JSON│
└──────────┬──────────────────────────────┘
           │ structured TripPlan
           ▼
       Frontend
```

## How it works

Four specialised agents run in sequence:

1. **Attraction agent** — searches POIs via the Amap MCP server
2. **Weather agent** — fetches a multi-day forecast
3. **Hotel agent** — finds accommodation matching your preference
4. **Planner agent** — combines all of the above into a structured JSON itinerary

The backend is a FastAPI app; the frontend is Vue 3 + Ant Design Vue.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.10+, FastAPI, Pydantic v2, hello-agents |
| Frontend | Vue 3, TypeScript, Vite, Ant Design Vue |
| LLM | DeepSeek (`deepseek-chat`) |
| Maps | Amap Web Services (MCP server + JS API) |
| Images | Unsplash API (optional) |

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
cp .env.example .env      # fill in your API keys
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API docs at `http://localhost:8000/docs`.

## Environment variables

| Variable | Description |
|----------|-------------|
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `AMAP_API_KEY` | Amap Web Services key |
| `UNSPLASH_ACCESS_KEY` | Unsplash access key (optional — images are skipped if not set) |

## Notes

- The Amap MCP server is pulled automatically via `npx @amap/amap-maps-mcp-server` — no manual install needed.
- If `hello-agents` is not installed, the app falls back to a single direct DeepSeek call.
- LLM generation typically takes 15–60 seconds depending on trip length.
