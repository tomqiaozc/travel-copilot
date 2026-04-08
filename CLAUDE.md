# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Travel Copilot — an AI-powered travel itinerary planner. Users upload travel guide screenshots (primarily Chinese/Xiaohongshu content), GPT-4o Vision extracts places, Azure Maps geocodes them, and an AI planner generates day-by-day itineraries with drag-and-drop reordering and map visualization.

## Repository Structure

Two independent projects (frontend + backend) in one repo. No monorepo tooling — each is developed separately.

- `frontend/` — React 19 + TypeScript SPA (Vite 8, Tailwind CSS 4, Zustand 5)
- `backend/` — Python FastAPI REST API
- `tests/` — Top-level integration tests (geocoding, extract+geocode E2E)
- `docs/` — Project documentation and TODOs

## Development Commands

### Frontend (`cd frontend`)

```bash
npm run dev          # Vite dev server (port 5173), proxies /api to localhost:8000
npm run build        # tsc -b && vite build
npm run lint         # ESLint
```

### Backend (`cd backend`)

```bash
uvicorn app.main:app --reload    # FastAPI dev server (port 8000)
pytest                           # Run all tests (asyncio_mode=auto)
pytest tests/test_foo.py         # Run a single test file
pytest tests/test_foo.py::test_bar  # Run a single test
```

### Top-level integration tests

```bash
cd tests && pytest               # Requires backend .env to be configured
```

## Environment Setup

### Backend (`backend/.env`)

Required for local dev (with `USE_LOCAL_DB=true`, only these are needed):
- `GITHUB_TOKEN` — GitHub Models API token (for GPT-4o)
- `AZURE_MAPS_KEY` — Azure Maps subscription key
- `AI_MODEL` — Model name (default: `gpt-4o`)
- `USE_LOCAL_DB=true` — Uses in-memory database, no Azure Cosmos needed

Production additionally needs: `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE`, `BLOB_CONNECTION_STRING`, `BLOB_CONTAINER`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_SECRET`

### Frontend (`frontend/.env`)

- `VITE_AZURE_MAPS_KEY` — Azure Maps key for map rendering
- `VITE_GOOGLE_CLIENT_ID` — Google OAuth client ID

## Architecture

### Backend (`backend/app/`)

Domain-driven modules, each with `router.py` (API), `models.py` (Pydantic), `repository.py` (data access):

- `auth/` — Google OAuth 2.0 + JWT auth. Dev-login endpoint bypasses OAuth locally.
- `trips/` — Trip CRUD
- `places/` — Place CRUD (types: attraction/restaurant/hotel/other)
- `images/` — Image upload (local filesystem in dev, Azure Blob in prod)
- `ai/` — Core AI features:
  - `extract.py` — GPT-4o Vision extracts places from screenshot images
  - `planner.py` — AI itinerary planning using coordinate distance matrices for proximity grouping
  - `github_models.py` — HTTP client for GitHub Models API (OpenAI-compatible endpoint)
- `maps/` — Geocoding and mapping:
  - `geocoding.py` — Multi-strategy parallel geocoding with cluster-based outlier detection
  - `distance.py` — Haversine distance calculations
  - `export.py` — Google Maps direction URL generation
- `db.py` / `db_memory.py` — Database abstraction; `USE_LOCAL_DB=true` switches to in-memory store with SQL-like query parsing

**API prefix:** All routes under `/api/`. Key endpoints:
- `POST /api/trips/{id}/extract` — AI extract places from uploaded images + geocode
- `POST /api/trips/{id}/plan` — AI itinerary planning
- `GET /api/trips/{id}/export/google-maps` — Export per-day Google Maps links

### Frontend (`frontend/src/`)

- `pages/` — Four route pages: LoginPage, TripsPage, TripDetailPage, PlannerPage
- `components/` — UI components (DayGroup with drag-and-drop, TripMap with Azure Maps, ExtractionModal, PlanPromptModal, etc.)
- `stores/` — Zustand stores: `auth.ts` (user/login state), `trip.ts` (trips/places CRUD + AI actions)
- `api/client.ts` — Fetch wrapper with JWT auth, auto-redirect on 401
- `types/index.ts` — Shared TypeScript interfaces

**Key frontend patterns:**
- Vite proxies `/api` to `http://localhost:8000` (configured in `vite.config.ts`)
- All server state managed through Zustand stores that wrap API calls
- Drag-and-drop itinerary via `@hello-pangea/dnd`
- Azure Maps SDK for interactive map with color-coded day markers and route lines

### AI Pipeline Flow

1. User uploads travel guide screenshots
2. GPT-4o Vision extracts place names/types/notes from images
3. Multi-strategy parallel geocoding (local name, English, Chinese variants) via Azure Maps Fuzzy Search
4. Cluster-based validation: compute median center, reverse-geocode for city hint, re-geocode outliers with geographic constraints
5. AI planner groups places by proximity using distance matrices, generates day schedule
6. User refines via drag-and-drop, exports to Google Maps

### Type Duplication

Types are duplicated between Python Pydantic models and TypeScript interfaces — there is no shared schema or code generation. Keep both in sync when modifying data structures.
