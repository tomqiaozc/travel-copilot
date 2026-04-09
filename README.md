# Travel Copilot

AI-powered travel itinerary planner. Upload travel guide screenshots (e.g. from Xiaohongshu/小红书), let GPT-4o Vision extract places, auto-geocode with Google Maps, then plan and organize your trip with drag-and-drop itineraries and interactive maps.

## Screenshots

### Trip Management
![Trips List](docs/screenshots/trips-list.png)

### Place Cards with Geocode Confidence
Upload screenshots or paste Google Maps links to add places. Each place shows a confidence indicator:
- Green — location verified
- Orange — location uncertain ("待确认"), needs manual check
- Red — geocoding failed ("缺少定位"), add a Google Maps link to fix

![Trip Detail](docs/screenshots/trip-detail.png)
![Place Cards](docs/screenshots/place-cards-confidence.png)

### Itinerary Planner with Map
Drag-and-drop day-by-day itinerary with color-coded map markers, route lines, and distance info. Export to KML for Google My Maps.

![Planner Page](docs/screenshots/planner-page.png)

## How It Works

1. **Create a trip** with destination and dates
2. **Upload travel guide screenshots** — GPT-4o Vision extracts place names, types, and notes
3. **Import from Google Maps** — upload Google Takeout CSV files to import your saved/favorited places, auto-filtered by trip destination proximity and smart-inserted into the optimal day/position
4. **Auto-geocode** — multi-strategy parallel geocoding via Google Maps with outlier detection
5. **Review places** — check confidence indicators, fix any red/orange places by pasting a Google Maps link
6. **Plan itinerary** — AI groups places by proximity into days, or drag-and-drop manually
7. **Export** — download KML file to import into Google My Maps

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, Zustand 5 |
| Backend | Python 3.9+, FastAPI, Pydantic |
| AI | GPT-4o Vision via GitHub Models API |
| Maps | Google Maps JavaScript API, Google Places API (New), Google Geocoding API |
| Database | Azure Cosmos DB (production), PostgreSQL or in-memory (local dev) |
| Storage | Azure Blob Storage (production), local filesystem (local dev) |
| Auth | Google OAuth 2.0 + JWT (production), dev-login bypass (local dev) |

## Local Development Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker (for local PostgreSQL, optional)
- API keys (see below)

### 1. Get API Keys

You need three API keys to run locally:

| Key | Where to Get | Used For |
|-----|-------------|----------|
| `GITHUB_TOKEN` | [GitHub Settings > Tokens](https://github.com/settings/tokens) — needs access to GitHub Models | AI vision extraction (GPT-4o) and trip planning |
| `GOOGLE_MAPS_API_KEY` | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — enable Maps JavaScript API, Geocoding API, Places API | Geocoding places, resolving Google Maps links, frontend map display |
| `VITE_GOOGLE_CLIENT_ID` | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — create OAuth 2.0 Client ID | Google login (optional for local dev, dev-login is auto-enabled) |

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Option A: PostgreSQL (recommended — data persists across restarts)

```bash
# Start PostgreSQL via Docker (from project root)
docker-compose up -d

# Create .env file
cat > .env << 'EOF'
GITHUB_TOKEN=your_github_token_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
AI_MODEL=gpt-4o
DATABASE_URL=postgresql://travel:travel@localhost:5432/travel_copilot
EOF

# Start the server
uvicorn app.main:app --reload
```

Tables are auto-created on first request. Data survives backend restarts. To reset, run `docker-compose down -v`.

#### Option B: In-memory (no Docker needed — data resets on restart)

```bash
# Create .env file
cat > .env << 'EOF'
GITHUB_TOKEN=your_github_token_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
AI_MODEL=gpt-4o
USE_LOCAL_DB=true
EOF

# Start the server
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env file
cat > .env << 'EOF'
VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
VITE_GOOGLE_CLIENT_ID=your_google_client_id_here
EOF

# Start the dev server
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies `/api` requests to the backend.

### 4. Login

With `USE_LOCAL_DB=true`, a **dev-login** endpoint is automatically available. The app will show a "Dev Login" button on the login page — no Google OAuth setup needed for local development.

## Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes | — | GitHub Models API token for GPT-4o |
| `GOOGLE_MAPS_API_KEY` | Yes | — | Google Maps Platform API key |
| `AI_MODEL` | No | `gpt-4o` | AI model name |
| `USE_LOCAL_DB` | No | `false` | `true` = in-memory DB, no Azure/Docker needed |
| `DATABASE_URL` | No | — | PostgreSQL connection string (e.g. `postgresql://travel:travel@localhost:5432/travel_copilot`). Takes priority over `USE_LOCAL_DB` |
| `COSMOS_ENDPOINT` | Prod | — | Azure Cosmos DB endpoint |
| `COSMOS_KEY` | Prod | — | Azure Cosmos DB key |
| `COSMOS_DATABASE` | No | `travel-copilot` | Cosmos database name |
| `BLOB_CONNECTION_STRING` | Prod | — | Azure Blob Storage connection string |
| `BLOB_CONTAINER` | No | `screenshots` | Blob container name |
| `GOOGLE_CLIENT_ID` | Prod | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Prod | — | Google OAuth client secret |
| `JWT_SECRET` | Prod | `dev-secret-change-in-prod` | JWT signing secret |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | Google Maps API key for map rendering |
| `VITE_GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID (dev-login works without it) |

## Development Commands

```bash
# Backend
cd backend
uvicorn app.main:app --reload       # Start dev server (port 8000)
pytest                               # Run all tests
pytest tests/test_foo.py::test_bar   # Run a single test

# Frontend
cd frontend
npm run dev       # Vite dev server (port 5173)
npm run build     # Type-check + production build
npm run lint      # ESLint

# Database (from project root)
docker-compose up -d                 # Start PostgreSQL
docker-compose down                  # Stop PostgreSQL (data preserved)
docker-compose down -v               # Stop PostgreSQL and delete all data
```

## Project Structure

```
├── backend/
│   └── app/
│       ├── ai/          # GPT-4o vision extraction & trip planning
│       ├── auth/        # Google OAuth + JWT + dev-login
│       ├── export/      # KML and Google Maps export endpoints
│       ├── google_import/ # Google Maps saved places import (Takeout CSV)
│       ├── maps/        # Geocoding (Places Text Search), distance calc, place resolver, opening hours
│       ├── places/      # Place CRUD
│       ├── trips/       # Trip CRUD
│       └── images/      # Screenshot upload & storage
├── frontend/
│   └── src/
│       ├── pages/       # LoginPage, TripsPage, TripDetailPage, PlannerPage
│       ├── components/  # DayGroup, TripMap, ExtractionModal, etc.
│       ├── stores/      # Zustand stores (auth, trip)
│       ├── utils/       # Google Maps links, opening hours helpers
│       └── api/         # API client with JWT auth
├── tests/               # Integration tests (geocoding accuracy, E2E)
└── docs/
    └── screenshots/     # Product screenshots
```
