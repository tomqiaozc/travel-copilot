# Travel Copilot — AI Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the AI-powered features: screenshot → POI extraction via claude-sonnet-4.6 Vision, intelligent itinerary planning via claude-sonnet-4.6, geocoding via Azure Maps, and Google Maps export.

**Architecture:** Two AI endpoints that call GitHub Models API (claude-sonnet-4.6). Extract endpoint sends images with a structured prompt, plan endpoint sends place list + distance matrix + optional user instructions. Azure Maps REST API for geocoding and distance calculation. Local-first development with mock AI responses for testing.

**Tech Stack:** Python FastAPI (extends backend-core), httpx (GitHub Models API), Azure Maps REST API, pytest

---

## File Structure

```
backend/app/
├── ai/
│   ├── __init__.py
│   ├── github_models.py      # GitHub Models API client (claude-sonnet-4.6)
│   ├── extract.py             # Screenshot → POI extraction logic
│   ├── planner.py             # Itinerary planning logic
│   └── router.py              # POST /extract, POST /plan endpoints
├── maps/
│   ├── __init__.py
│   ├── geocoding.py           # Azure Maps geocoding (name → lat/lng)
│   ├── distance.py            # Azure Maps distance matrix
│   └── export.py              # Google Maps URL generation
├── export/
│   ├── __init__.py
│   └── router.py              # GET /export/google-maps endpoint
backend/tests/
├── test_ai_extract.py
├── test_ai_planner.py
├── test_maps.py
├── test_export.py
└── fixtures/
    └── sample_ocr_response.json  # Mock AI response for testing
```

---

### Task 1: GitHub Models API Client

**Files:**
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/github_models.py`
- Modify: `backend/app/config.py` — add GitHub Models config

- [ ] **Step 1: Add GitHub Models config to config.py**

Append to the `Settings` class in `backend/app/config.py`:

```python
    # GitHub Models
    github_token: str = ""
    github_models_endpoint: str = "https://models.inference.ai.azure.com"
    ai_model: str = "claude-sonnet-4.6"
```

- [ ] **Step 2: Create GitHub Models client**

```python
# backend/app/ai/__init__.py
```

```python
# backend/app/ai/github_models.py
import base64

import httpx

from app.config import settings


async def chat_completion(messages: list[dict], max_tokens: int = 4096) -> str:
    """Send a chat completion request to GitHub Models API."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{settings.github_models_endpoint}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.ai_model,
                "messages": messages,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def vision_completion(prompt: str, image_data_list: list[bytes], max_tokens: int = 4096) -> str:
    """Send images + prompt to GitHub Models API (Vision)."""
    content = [{"type": "text", "text": prompt}]
    for img_data in image_data_list:
        b64 = base64.b64encode(img_data).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })

    messages = [{"role": "user", "content": content}]
    return await chat_completion(messages, max_tokens=max_tokens)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/ai/ backend/app/config.py
git commit -m "feat(backend): add GitHub Models API client for claude-sonnet-4.6"
```

---

### Task 2: Screenshot → POI Extraction

**Files:**
- Create: `backend/app/ai/extract.py`
- Create: `backend/tests/test_ai_extract.py`
- Create: `backend/tests/fixtures/sample_ocr_response.json`

- [ ] **Step 1: Create sample AI response fixture**

```json
// backend/tests/fixtures/sample_ocr_response.json
[
  {"name": "浅草寺", "type": "attraction"},
  {"name": "晴空塔", "type": "attraction"},
  {"name": "一兰拉面 浅草店", "type": "restaurant"},
  {"name": "东京站酒店", "type": "hotel"},
  {"name": "涩谷十字路口", "type": "attraction"}
]
```

- [ ] **Step 2: Write failing test for extraction**

```python
# backend/tests/test_ai_extract.py
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.extract import extract_places_from_images

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_extract_places_from_images():
    sample_response = (FIXTURES_DIR / "sample_ocr_response.json").read_text()

    with patch("app.ai.extract.vision_completion", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = sample_response
        result = await extract_places_from_images([b"fake-image-data"])

    assert len(result) == 5
    assert result[0]["name"] == "浅草寺"
    assert result[0]["type"] == "attraction"
    assert result[2]["type"] == "restaurant"


@pytest.mark.asyncio
async def test_extract_places_handles_markdown_wrapped_json():
    """AI sometimes wraps JSON in markdown code blocks."""
    wrapped = '```json\n[{"name": "Test Place", "type": "attraction"}]\n```'

    with patch("app.ai.extract.vision_completion", new_callable=AsyncMock) as mock_vision:
        mock_vision.return_value = wrapped
        result = await extract_places_from_images([b"fake-image-data"])

    assert len(result) == 1
    assert result[0]["name"] == "Test Place"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ai_extract.py -v`
Expected: FAIL

- [ ] **Step 4: Implement extraction logic**

```python
# backend/app/ai/extract.py
import json
import re

from app.ai.github_models import vision_completion

EXTRACT_PROMPT = """You are analyzing travel guide screenshots (likely from Chinese social media like Xiaohongshu/小红书).

Extract ALL places mentioned in these images. For each place, identify:
- name: The place name (keep original language, e.g., Chinese or Japanese)
- type: One of "attraction", "restaurant", "hotel", or "other"

Return a JSON array. Example:
[
  {"name": "浅草寺", "type": "attraction"},
  {"name": "一兰拉面", "type": "restaurant"}
]

Rules:
- Extract every place mentioned, including restaurants, hotels, shops, and landmarks
- If the type is ambiguous, use "other"
- Do NOT include transportation methods or general area names (like "东京") as places
- Return ONLY the JSON array, no other text"""


def _parse_json_response(text: str) -> list[dict]:
    """Parse JSON from AI response, handling markdown code blocks."""
    # Strip markdown code block wrapper if present
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


async def extract_places_from_images(image_data_list: list[bytes]) -> list[dict]:
    """Extract POI list from screenshot images using AI Vision."""
    response = await vision_completion(EXTRACT_PROMPT, image_data_list)
    return _parse_json_response(response)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_ai_extract.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/ai/extract.py backend/tests/test_ai_extract.py backend/tests/fixtures/
git commit -m "feat(backend): add AI screenshot extraction with Vision API"
```

---

### Task 3: Azure Maps Geocoding & Distance

**Files:**
- Create: `backend/app/maps/__init__.py`
- Create: `backend/app/maps/geocoding.py`
- Create: `backend/app/maps/distance.py`
- Create: `backend/tests/test_maps.py`
- Modify: `backend/app/config.py` — add Azure Maps config

- [ ] **Step 1: Add Azure Maps config**

Append to the `Settings` class in `backend/app/config.py`:

```python
    # Azure Maps
    azure_maps_key: str = ""
```

- [ ] **Step 2: Write failing tests**

```python
# backend/tests/test_maps.py
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.maps.geocoding import geocode_place, geocode_places
from app.maps.distance import calculate_distance_km


@pytest.mark.asyncio
async def test_geocode_place():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "position": {"lat": 35.7148, "lon": 139.7967},
                "address": {"freeformAddress": "Senso-ji, Tokyo"},
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.maps.geocoding.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await geocode_place("浅草寺")

    assert result["latitude"] == 35.7148
    assert result["longitude"] == 139.7967


def test_calculate_distance_km():
    # Tokyo Station to Senso-ji is roughly 4-5km
    dist = calculate_distance_km(35.6812, 139.7671, 35.7148, 139.7967)
    assert 3.0 < dist < 6.0


def test_calculate_distance_same_point():
    dist = calculate_distance_km(35.6812, 139.7671, 35.6812, 139.7671)
    assert dist == 0.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_maps.py -v`
Expected: FAIL

- [ ] **Step 4: Implement geocoding**

```python
# backend/app/maps/__init__.py
```

```python
# backend/app/maps/geocoding.py
import httpx

from app.config import settings


async def geocode_place(name: str) -> dict:
    """Geocode a place name to lat/lng using Azure Maps."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://atlas.microsoft.com/search/address/json",
            params={
                "api-version": "1.0",
                "subscription-key": settings.azure_maps_key,
                "query": name,
                "limit": 1,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("results"):
        return {"latitude": None, "longitude": None}

    pos = data["results"][0]["position"]
    return {"latitude": pos["lat"], "longitude": pos["lon"]}


async def geocode_places(names: list[str]) -> list[dict]:
    """Geocode multiple place names."""
    results = []
    for name in names:
        result = await geocode_place(name)
        results.append(result)
    return results
```

- [ ] **Step 5: Implement distance calculation**

```python
# backend/app/maps/distance.py
import math


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    if lat1 == lat2 and lon1 == lon2:
        return 0.0

    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_maps.py -v`
Expected: 3 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/maps/ backend/app/config.py backend/tests/test_maps.py
git commit -m "feat(backend): add Azure Maps geocoding and distance calculation"
```

---

### Task 4: AI Itinerary Planner

**Files:**
- Create: `backend/app/ai/planner.py`
- Create: `backend/tests/test_ai_planner.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_ai_planner.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.planner import plan_itinerary


@pytest.mark.asyncio
async def test_plan_itinerary():
    places = [
        {"id": "p1", "name": "浅草寺", "type": "attraction", "latitude": 35.7148, "longitude": 139.7967},
        {"id": "p2", "name": "晴空塔", "type": "attraction", "latitude": 35.7101, "longitude": 139.8107},
        {"id": "p3", "name": "涩谷十字路口", "type": "attraction", "latitude": 35.6595, "longitude": 139.7004},
        {"id": "p4", "name": "原宿竹下通", "type": "attraction", "latitude": 35.6702, "longitude": 139.7026},
    ]

    ai_response = json.dumps([
        {
            "day": 1,
            "places": [
                {"id": "p1", "order": 1},
                {"id": "p2", "order": 2},
            ],
        },
        {
            "day": 2,
            "places": [
                {"id": "p3", "order": 1},
                {"id": "p4", "order": 2},
            ],
        },
    ])

    with patch("app.ai.planner.chat_completion", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = ai_response
        result = await plan_itinerary(places, num_days=2, user_prompt="")

    assert len(result) == 2
    assert result[0]["day"] == 1
    assert len(result[0]["places"]) == 2
    assert result[0]["places"][0]["id"] == "p1"


@pytest.mark.asyncio
async def test_plan_itinerary_with_user_prompt():
    places = [
        {"id": "p1", "name": "浅草寺", "type": "attraction", "latitude": 35.7148, "longitude": 139.7967},
    ]

    ai_response = json.dumps([{"day": 1, "places": [{"id": "p1", "order": 1}]}])

    with patch("app.ai.planner.chat_completion", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = ai_response
        result = await plan_itinerary(places, num_days=1, user_prompt="轻松一点")

    # Verify user prompt was included in the AI call
    call_args = mock_chat.call_args[0][0]  # messages list
    system_msg = call_args[0]["content"]
    assert "轻松一点" in call_args[1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ai_planner.py -v`
Expected: FAIL

- [ ] **Step 3: Implement planner**

```python
# backend/app/ai/planner.py
import json
import re

from app.ai.github_models import chat_completion
from app.maps.distance import calculate_distance_km

PLANNER_SYSTEM_PROMPT = """You are a travel itinerary planner. Given a list of places with their coordinates and a number of days, organize them into a daily schedule.

Rules:
- Group nearby places together on the same day to minimize travel distance
- Each day should have a reasonable number of places (2-5)
- Consider place types: try to include a mix of attractions and restaurants each day
- Hotels don't need to be scheduled in the daily itinerary

Return a JSON array of daily schedules. Example:
[
  {"day": 1, "places": [{"id": "p1", "order": 1}, {"id": "p2", "order": 2}]},
  {"day": 2, "places": [{"id": "p3", "order": 1}]}
]

Return ONLY the JSON array, no other text."""


def _build_places_description(places: list[dict]) -> str:
    """Build a text description of places with distances."""
    lines = []
    for p in places:
        lat = p.get("latitude", "unknown")
        lng = p.get("longitude", "unknown")
        lines.append(f"- {p['id']}: {p['name']} ({p['type']}) at ({lat}, {lng})")

    # Add distance matrix for key pairs
    if len(places) > 1:
        lines.append("\nDistances between places:")
        for i, p1 in enumerate(places):
            for p2 in places[i + 1 :]:
                if p1.get("latitude") and p2.get("latitude"):
                    dist = calculate_distance_km(
                        p1["latitude"], p1["longitude"],
                        p2["latitude"], p2["longitude"],
                    )
                    lines.append(f"  {p1['name']} ↔ {p2['name']}: {dist:.1f} km")

    return "\n".join(lines)


def _parse_json_response(text: str) -> list[dict]:
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1)
    return json.loads(text.strip())


async def plan_itinerary(
    places: list[dict], num_days: int, user_prompt: str = ""
) -> list[dict]:
    """Use AI to plan an itinerary grouping places by proximity."""
    # Filter out hotels and places without coordinates
    plannable = [p for p in places if p.get("type") != "hotel" and p.get("latitude")]

    places_desc = _build_places_description(plannable)

    user_message = f"Plan a {num_days}-day itinerary for these places:\n\n{places_desc}"
    if user_prompt:
        user_message += f"\n\nAdditional instructions from user: {user_prompt}"

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    response = await chat_completion(messages)
    return _parse_json_response(response)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ai_planner.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/planner.py backend/tests/test_ai_planner.py
git commit -m "feat(backend): add AI itinerary planner with user prompt support"
```

---

### Task 5: AI Router — Extract & Plan Endpoints

**Files:**
- Create: `backend/app/ai/router.py`
- Modify: `backend/app/main.py` — register AI router

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_ai_extract.py`:

```python
from unittest.mock import patch, AsyncMock, MagicMock
from tests.conftest import make_auth_headers


def test_extract_endpoint(client, mock_get_container, mock_container):
    import io

    # Mock trip exists
    mock_container.read_item.return_value = {"id": "t1", "user_id": "user-1"}

    sample_places = [{"name": "浅草寺", "type": "attraction"}]

    with patch("app.ai.router.extract_places_from_images", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = sample_places

        with patch("app.images.repository.get_blob_container_client") as mock_blob:
            mock_blob_client = MagicMock()
            mock_blob_client.url = "https://blob.url/test.png"
            mock_blob.return_value.get_blob_client.return_value = mock_blob_client

            files = [("images", ("test.png", io.BytesIO(b"fake"), "image/png"))]
            headers = make_auth_headers()
            resp = client.post("/api/trips/t1/extract", headers=headers, files=files)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["places"]) == 1
    assert data["places"][0]["name"] == "浅草寺"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ai_extract.py::test_extract_endpoint -v`
Expected: FAIL

- [ ] **Step 3: Implement AI router**

```python
# backend/app/ai/router.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.ai.extract import extract_places_from_images
from app.ai.planner import plan_itinerary
from app.images import repository as image_repo
from app.places.repository import list_places, update_place
from app.maps.geocoding import geocode_places
from app.trips.repository import get_trip

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["ai"])


class PlanRequest(BaseModel):
    user_prompt: str = ""


@router.post("/extract")
async def extract_from_screenshots(
    trip_id: str,
    images: list[UploadFile],
    user: dict = Depends(get_current_user),
):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")

    # Upload images to Blob Storage
    image_data_list = []
    for image in images:
        data = await image.read()
        image_data_list.append(data)
        image_repo.upload_image(
            trip_id=trip_id,
            filename=image.filename or "image.png",
            data=data,
            content_type=image.content_type or "image/png",
        )

    # Extract places using AI Vision
    places = await extract_places_from_images(image_data_list)
    return {"places": places}


@router.post("/plan")
async def plan_trip(
    trip_id: str,
    body: PlanRequest,
    user: dict = Depends(get_current_user),
):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    places = list_places(trip_id)
    if not places:
        raise HTTPException(status_code=400, detail="No places to plan")

    # Geocode places that don't have coordinates yet
    needs_geocoding = [p for p in places if p.get("latitude") is None]
    if needs_geocoding:
        geo_results = await geocode_places([p["name"] for p in needs_geocoding])
        for place, geo in zip(needs_geocoding, geo_results):
            place["latitude"] = geo["latitude"]
            place["longitude"] = geo["longitude"]
            update_place(place["id"], trip_id, {
                "latitude": geo["latitude"],
                "longitude": geo["longitude"],
            })

    # Calculate number of days from trip dates
    from datetime import date

    start = date.fromisoformat(str(trip["start_date"]))
    end = date.fromisoformat(str(trip["end_date"]))
    num_days = (end - start).days + 1

    # Plan with AI
    schedule = await plan_itinerary(places, num_days, body.user_prompt)

    # Apply schedule to places
    for day_plan in schedule:
        for place_ref in day_plan["places"]:
            update_place(place_ref["id"], trip_id, {
                "day_number": day_plan["day"],
                "order_in_day": place_ref["order"],
            })

    return {"schedule": schedule}
```

- [ ] **Step 4: Register AI router in main.py**

Add to `backend/app/main.py`:

```python
from app.ai.router import router as ai_router

app.include_router(ai_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ai_extract.py -v`
Expected: All passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/ai/router.py backend/app/main.py backend/tests/test_ai_extract.py
git commit -m "feat(backend): add AI extract and plan API endpoints"
```

---

### Task 6: Google Maps Export

**Files:**
- Create: `backend/app/maps/export.py`
- Create: `backend/app/export/__init__.py`
- Create: `backend/app/export/router.py`
- Create: `backend/tests/test_export.py`
- Modify: `backend/app/main.py` — register export router

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_export.py
from app.maps.export import generate_google_maps_url, generate_export_links


def test_generate_google_maps_url_single_place():
    places = [{"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967}]
    url = generate_google_maps_url(places)
    assert "google.com/maps/dir/" in url
    assert "35.7148" in url


def test_generate_google_maps_url_multiple_places():
    places = [
        {"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967},
        {"name": "晴空塔", "latitude": 35.7101, "longitude": 139.8107},
        {"name": "一兰拉面", "latitude": 35.7120, "longitude": 139.7960},
    ]
    url = generate_google_maps_url(places)
    assert "google.com/maps/dir/" in url


def test_generate_export_links():
    places = [
        {"name": "浅草寺", "latitude": 35.7148, "longitude": 139.7967, "day_number": 1, "order_in_day": 1},
        {"name": "晴空塔", "latitude": 35.7101, "longitude": 139.8107, "day_number": 1, "order_in_day": 2},
        {"name": "涩谷", "latitude": 35.6595, "longitude": 139.7004, "day_number": 2, "order_in_day": 1},
    ]
    links = generate_export_links(places)
    assert len(links) == 2
    assert links[0]["day"] == 1
    assert "google.com/maps/dir/" in links[0]["url"]
    assert links[1]["day"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_export.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Google Maps URL generation**

```python
# backend/app/maps/export.py
from urllib.parse import quote


def generate_google_maps_url(places: list[dict]) -> str:
    """Generate a Google Maps directions URL for a list of ordered places."""
    if not places:
        return ""

    waypoints = []
    for p in places:
        lat = p.get("latitude")
        lng = p.get("longitude")
        if lat and lng:
            waypoints.append(f"{lat},{lng}")

    if not waypoints:
        return ""

    # Google Maps directions URL format
    base = "https://www.google.com/maps/dir/"
    return base + "/".join(waypoints)


def generate_export_links(places: list[dict]) -> list[dict]:
    """Generate per-day Google Maps links."""
    # Group by day
    days: dict[int, list[dict]] = {}
    for p in places:
        day = p.get("day_number")
        if day is not None:
            days.setdefault(day, []).append(p)

    # Sort each day by order_in_day
    links = []
    for day_num in sorted(days.keys()):
        day_places = sorted(days[day_num], key=lambda x: x.get("order_in_day", 0))
        url = generate_google_maps_url(day_places)
        links.append({"day": day_num, "url": url, "place_count": len(day_places)})

    return links
```

- [ ] **Step 4: Implement export router**

```python
# backend/app/export/__init__.py
```

```python
# backend/app/export/router.py
from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user
from app.maps.export import generate_export_links
from app.places.repository import list_places
from app.trips.repository import get_trip

router = APIRouter(prefix="/api/trips/{trip_id}/export", tags=["export"])


@router.get("/google-maps")
async def export_google_maps(trip_id: str, user: dict = Depends(get_current_user)):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    places = list_places(trip_id)
    links = generate_export_links(places)
    return {"links": links}
```

- [ ] **Step 5: Register export router in main.py**

Add to `backend/app/main.py`:

```python
from app.export.router import router as export_router

app.include_router(export_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_export.py -v`
Expected: 3 passed

- [ ] **Step 7: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/app/maps/export.py backend/app/export/ backend/app/main.py backend/tests/test_export.py
git commit -m "feat(backend): add Google Maps export with per-day route links"
```
