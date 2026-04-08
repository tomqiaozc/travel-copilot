# Place Cards Enhancement + KML Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add editable place cards with Google Maps links, add-place-by-Google-Maps-URL, and KML file export for Google My Maps import.

**Architecture:** Backend changes: fix `google_place_id` persistence, add coordinates to `PlaceUpdate`, create a Google Maps URL resolver (`place_resolver.py`), and add KML generation to `export.py`. Frontend changes: inline editing on TripDetailPage place cards, Google Maps links on cards and InfoWindow, URL-based place adding in PlaceForm, and KML download replacing the directions-URL export modal.

**Tech Stack:** Python/FastAPI, httpx, xml.etree.ElementTree, React 19, TypeScript, Zustand, Tailwind CSS

---

### Task 1: Fix `google_place_id` Persistence + Add Coordinates to PlaceUpdate

**Files:**
- Modify: `backend/app/places/repository.py:22-35`
- Modify: `backend/app/places/models.py:20-28`
- Test: `backend/tests/test_export.py`

- [ ] **Step 1: Write test for `google_place_id` persistence**

Add to `backend/tests/test_export.py`:

```python
def test_create_place_persists_google_place_id():
    """Verify google_place_id is included in the document created by create_place."""
    from app.places.repository import create_place
    import app.db as db

    # Ensure local DB is initialized
    db.get_container("places")

    data = {
        "name": "浅草寺",
        "type": "attraction",
        "note": "",
        "latitude": 35.7148,
        "longitude": 139.7967,
        "google_place_id": "ChIJ82XhAEuMGGARqBqkPGiMaMA",
    }
    result = create_place("test-trip-id", data, source="ai_extracted")
    assert result["google_place_id"] == "ChIJ82XhAEuMGGARqBqkPGiMaMA"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_export.py::test_create_place_persists_google_place_id -v`
Expected: FAIL — `KeyError: 'google_place_id'` because `create_place` doesn't include it in the doc.

- [ ] **Step 3: Fix `create_place` to include `google_place_id`**

In `backend/app/places/repository.py`, add `google_place_id` to the doc dict in `create_place()`. Change lines 22-35 to:

```python
    doc = {
        "id": str(uuid.uuid4()),
        "trip_id": trip_id,
        "name": data["name"],
        "type": data["type"],
        "note": data.get("note", ""),
        "name_local": data.get("name_local"),
        "name_en": data.get("name_en"),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "google_place_id": data.get("google_place_id"),
        "source": data.get("source") or source,
        "day_number": data.get("day_number"),
        "order_in_day": data.get("order_in_day", 0),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_export.py::test_create_place_persists_google_place_id -v`
Expected: PASS

- [ ] **Step 5: Add `latitude` and `longitude` to `PlaceUpdate`**

In `backend/app/places/models.py`, change `PlaceUpdate` (lines 20-28) to:

```python
class PlaceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    note: Optional[str] = None
    name_local: Optional[str] = None
    name_en: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    day_number: Optional[int] = None
    order_in_day: Optional[int] = None
```

- [ ] **Step 6: Run all existing tests to verify nothing breaks**

Run: `cd backend && python3 -m pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/places/repository.py backend/app/places/models.py backend/tests/test_export.py
git commit -m "fix: persist google_place_id in create_place and add coords to PlaceUpdate"
```

---

### Task 2: Google Maps URL Resolver (Backend)

**Files:**
- Create: `backend/app/maps/place_resolver.py`
- Modify: `backend/app/places/router.py:1-49`
- Create: `backend/tests/test_place_resolver.py`

- [ ] **Step 1: Write tests for URL parsing and type mapping**

Create `backend/tests/test_place_resolver.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.maps.place_resolver import (
    parse_google_maps_url,
    map_google_type_to_app_type,
    resolve_google_maps_link,
)


def test_parse_place_id_from_full_url():
    url = "https://www.google.com/maps/place/Senso-ji/data=!4m6!3m5!1s0x60188ec1a21c296d:0x23899be09b99fa02!8m2!3d35.7147651!4d139.7966553"
    result = parse_google_maps_url(url)
    assert result["place_id"] == "0x60188ec1a21c296d:0x23899be09b99fa02"


def test_parse_coordinates_from_url():
    url = "https://www.google.com/maps/place/Senso-ji/@35.7147651,139.7966553,17z/"
    result = parse_google_maps_url(url)
    assert abs(result["lat"] - 35.7147651) < 0.0001
    assert abs(result["lng"] - 139.7966553) < 0.0001


def test_parse_place_url_with_ftid():
    url = "https://www.google.com/maps/place/Some+Place/@35.0,135.0,15z/data=!4m2!3m1!1s0xabc:0xdef"
    result = parse_google_maps_url(url)
    assert result["place_id"] == "0xabc:0xdef"


def test_parse_invalid_url():
    with pytest.raises(ValueError, match="Not a Google Maps URL"):
        parse_google_maps_url("https://example.com/not-google")


def test_map_google_type_restaurant():
    assert map_google_type_to_app_type("restaurant") == "restaurant"
    assert map_google_type_to_app_type("cafe") == "restaurant"
    assert map_google_type_to_app_type("bakery") == "restaurant"
    assert map_google_type_to_app_type("bar") == "restaurant"


def test_map_google_type_hotel():
    assert map_google_type_to_app_type("lodging") == "hotel"
    assert map_google_type_to_app_type("hotel") == "hotel"


def test_map_google_type_attraction():
    assert map_google_type_to_app_type("tourist_attraction") == "attraction"
    assert map_google_type_to_app_type("museum") == "attraction"
    assert map_google_type_to_app_type("park") == "attraction"


def test_map_google_type_other():
    assert map_google_type_to_app_type("gas_station") == "other"
    assert map_google_type_to_app_type("unknown_type") == "other"
    assert map_google_type_to_app_type(None) == "other"


@pytest.mark.asyncio
async def test_resolve_google_maps_link_with_place_id():
    mock_place_details_response = {
        "displayName": {"text": "浅草寺"},
        "location": {"latitude": 35.7148, "longitude": 139.7967},
        "primaryType": "tourist_attraction",
        "formattedAddress": "2-3-1 Asakusa, Taito City, Tokyo",
        "id": "ChIJ82XhAEuMGGARqBqkPGiMaMA",
    }

    with patch("app.maps.place_resolver.follow_redirects") as mock_redirect, \
         patch("app.maps.place_resolver.fetch_place_details") as mock_details:
        # Short link resolves to a full URL with place_id
        mock_redirect.return_value = "https://www.google.com/maps/place/Senso-ji/@35.7148,139.7967,17z/data=!4m2!3m1!1s0x60188ec1a21c296d:0x23899be09b99fa02"
        mock_details.return_value = mock_place_details_response

        result = await resolve_google_maps_link("https://maps.app.goo.gl/abc123")

        assert result["name"] == "浅草寺"
        assert result["type"] == "attraction"
        assert abs(result["latitude"] - 35.7148) < 0.001
        assert abs(result["longitude"] - 139.7967) < 0.001
        assert result["google_place_id"] == "ChIJ82XhAEuMGGARqBqkPGiMaMA"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_place_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.maps.place_resolver'`

- [ ] **Step 3: Implement `place_resolver.py`**

Create `backend/app/maps/place_resolver.py`:

```python
from __future__ import annotations

import re
import logging
from urllib.parse import urlparse, unquote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Type mapping from Google's primaryType to our app types
RESTAURANT_TYPES = {
    "restaurant", "cafe", "bakery", "bar", "meal_delivery",
    "meal_takeaway", "food", "coffee_shop",
}
HOTEL_TYPES = {"lodging", "hotel", "motel", "hostel", "guest_house"}
ATTRACTION_TYPES = {
    "tourist_attraction", "museum", "park", "temple", "church",
    "mosque", "synagogue", "hindu_temple", "amusement_park", "zoo",
    "aquarium", "art_gallery", "stadium", "castle", "shrine",
}


def map_google_type_to_app_type(google_type: str | None) -> str:
    if not google_type:
        return "other"
    t = google_type.lower()
    if t in RESTAURANT_TYPES:
        return "restaurant"
    if t in HOTEL_TYPES:
        return "hotel"
    if t in ATTRACTION_TYPES:
        return "attraction"
    return "other"


def parse_google_maps_url(url: str) -> dict:
    """Extract place_id and/or coordinates from a Google Maps URL.

    Returns dict with optional keys: place_id, lat, lng, name.
    Raises ValueError if not a Google Maps URL.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if not any(h in host for h in ["google.com", "google.co", "goo.gl"]):
        raise ValueError("Not a Google Maps URL")

    result: dict = {}

    # Extract place_id from data parameter: !1s<place_id>
    # Format: !1s0x60188ec1a21c296d:0x23899be09b99fa02
    place_id_match = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", url)
    if place_id_match:
        result["place_id"] = place_id_match.group(1)

    # Extract coordinates from /@lat,lng pattern
    coord_match = re.search(r"/@(-?\d+\.?\d*),(-?\d+\.?\d*)", url)
    if coord_match:
        result["lat"] = float(coord_match.group(1))
        result["lng"] = float(coord_match.group(2))

    # Extract place name from /place/Name/ pattern
    name_match = re.search(r"/place/([^/@]+)", parsed.path)
    if name_match:
        result["name"] = unquote(name_match.group(1)).replace("+", " ")

    return result


async def follow_redirects(url: str) -> str:
    """Follow HTTP redirects to get the final URL."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        resp = await client.get(url)
        return str(resp.url)


async def fetch_place_details(place_id: str) -> dict:
    """Call Google Places API (New) to get place details.

    Uses the places.googleapis.com endpoint with field mask.
    """
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "id,displayName,location,primaryType,formattedAddress",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Place Details API error: {resp.status_code} {resp.text}")
        return resp.json()


async def geocode_to_place_id(query: str, lat: float | None = None, lng: float | None = None) -> str | None:
    """Use Google Geocoding API to find a place_id from name/coordinates."""
    params: dict = {"key": settings.google_maps_api_key}
    if lat is not None and lng is not None:
        params["latlng"] = f"{lat},{lng}"
    else:
        params["address"] = query

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
        )
        data = resp.json()
        if data.get("results"):
            return data["results"][0].get("place_id")
    return None


async def resolve_google_maps_link(url: str) -> dict:
    """Resolve a Google Maps URL (short or full) into place details.

    Returns: {name, type, latitude, longitude, google_place_id, formatted_address}
    Raises ValueError on invalid URL or resolution failure.
    """
    # Step 1: Follow redirects if short link
    if "goo.gl" in url or "maps.app" in url:
        resolved_url = await follow_redirects(url)
    else:
        resolved_url = url

    # Step 2: Parse the URL
    parsed = parse_google_maps_url(resolved_url)

    # Step 3: Get place_id if not already found
    google_place_id = parsed.get("place_id")
    if not google_place_id:
        # Try geocoding with name or coordinates
        name = parsed.get("name", "")
        lat = parsed.get("lat")
        lng = parsed.get("lng")
        google_place_id = await geocode_to_place_id(name, lat, lng)
        if not google_place_id:
            raise ValueError("Could not resolve place from URL")

    # Step 4: Get place details
    details = await fetch_place_details(google_place_id)

    display_name = details.get("displayName", {}).get("text", parsed.get("name", "Unknown"))
    location = details.get("location", {})
    primary_type = details.get("primaryType")

    return {
        "name": display_name,
        "type": map_google_type_to_app_type(primary_type),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "google_place_id": details.get("id", google_place_id),
        "formatted_address": details.get("formattedAddress", ""),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_place_resolver.py -v`
Expected: All PASS

- [ ] **Step 5: Add the resolve endpoint to places router**

In `backend/app/places/router.py`, add the import and new endpoint. The full file becomes:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.places.models import PlaceCreate, PlaceUpdate
from app.places import repository
from app.trips.repository import get_trip
from app.maps.place_resolver import resolve_google_maps_link

router = APIRouter(prefix="/api/trips/{trip_id}/places", tags=["places"])


class GoogleLinkRequest(BaseModel):
    url: str


def _verify_trip_access(trip_id: str, user: dict):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("")
async def list_places(trip_id: str, user: dict = Depends(get_current_user)):
    _verify_trip_access(trip_id, user)
    return repository.list_places(trip_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_place(
    trip_id: str, body: PlaceCreate, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    return repository.create_place(trip_id, body.model_dump(), source=body.source or "manual")


@router.put("/{place_id}")
async def update_place(
    trip_id: str, place_id: str, body: PlaceUpdate, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    place = repository.update_place(place_id, trip_id, body.model_dump(exclude_none=True))
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_place(
    trip_id: str, place_id: str, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    repository.delete_place(place_id, trip_id)


@router.post("/resolve-google-link")
async def resolve_google_link(
    trip_id: str, body: GoogleLinkRequest, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    try:
        result = await resolve_google_maps_link(body.url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 6: Run all backend tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/maps/place_resolver.py backend/app/places/router.py backend/tests/test_place_resolver.py
git commit -m "feat: add Google Maps URL resolver endpoint"
```

---

### Task 3: KML Export (Backend)

**Files:**
- Modify: `backend/app/maps/export.py`
- Modify: `backend/app/export/router.py`
- Test: `backend/tests/test_export.py`

- [ ] **Step 1: Write test for `generate_kml`**

Add to `backend/tests/test_export.py`:

```python
import xml.etree.ElementTree as ET
from app.maps.export import generate_kml


def test_generate_kml_basic_structure():
    places = [
        {"name": "浅草寺", "type": "attraction", "note": "Historic temple", "latitude": 35.7148, "longitude": 139.7967, "day_number": 1, "order_in_day": 1},
        {"name": "晴空塔", "type": "attraction", "note": "", "latitude": 35.7101, "longitude": 139.8107, "day_number": 1, "order_in_day": 2},
        {"name": "涩谷", "type": "attraction", "note": "Shopping", "latitude": 35.6595, "longitude": 139.7004, "day_number": 2, "order_in_day": 1},
    ]
    kml = generate_kml(places, "Tokyo Trip")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    doc = root.find("kml:Document", ns)
    assert doc is not None
    assert doc.find("kml:name", ns).text == "Tokyo Trip"

    folders = doc.findall("kml:Folder", ns)
    assert len(folders) == 2  # Day 1 and Day 2

    assert folders[0].find("kml:name", ns).text == "Day 1"
    placemarks = folders[0].findall("kml:Placemark", ns)
    assert len(placemarks) == 2
    assert placemarks[0].find("kml:name", ns).text == "浅草寺"
    coords = placemarks[0].find("kml:Point/kml:coordinates", ns).text
    assert coords == "139.7967,35.7148,0"

    assert folders[1].find("kml:name", ns).text == "Day 2"


def test_generate_kml_with_unassigned():
    places = [
        {"name": "浅草寺", "type": "attraction", "note": "", "latitude": 35.7148, "longitude": 139.7967, "day_number": 1, "order_in_day": 1},
        {"name": "未分配", "type": "other", "note": "", "latitude": 35.6, "longitude": 139.7, "day_number": None, "order_in_day": 0},
    ]
    kml = generate_kml(places, "Test")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    folders = root.find("kml:Document", ns).findall("kml:Folder", ns)
    assert len(folders) == 2
    assert folders[1].find("kml:name", ns).text == "Unassigned"


def test_generate_kml_skips_places_without_coordinates():
    places = [
        {"name": "有坐标", "type": "attraction", "note": "", "latitude": 35.7, "longitude": 139.8, "day_number": 1, "order_in_day": 1},
        {"name": "无坐标", "type": "other", "note": "", "latitude": None, "longitude": None, "day_number": 1, "order_in_day": 2},
    ]
    kml = generate_kml(places, "Test")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    placemarks = root.find("kml:Document/kml:Folder", ns).findall("kml:Placemark", ns)
    assert len(placemarks) == 1
    assert placemarks[0].find("kml:name", ns).text == "有坐标"


def test_generate_kml_description_format():
    places = [
        {"name": "一兰拉面", "type": "restaurant", "note": "Must try tonkotsu", "latitude": 35.7, "longitude": 139.8, "day_number": 1, "order_in_day": 1},
    ]
    kml = generate_kml(places, "Test")
    root = ET.fromstring(kml)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    desc = root.find("kml:Document/kml:Folder/kml:Placemark/kml:description", ns).text
    assert "restaurant" in desc
    assert "Must try tonkotsu" in desc
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_export.py::test_generate_kml_basic_structure -v`
Expected: FAIL — `ImportError: cannot import name 'generate_kml'`

- [ ] **Step 3: Implement `generate_kml` in export.py**

Add to `backend/app/maps/export.py` (keep existing functions, add at the end):

```python
import xml.etree.ElementTree as ET


def generate_kml(places: list, trip_name: str) -> str:
    """Generate a KML file with places grouped by day as folders."""
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = ET.SubElement(kml, "Document")
    ET.SubElement(document, "name").text = trip_name

    # Group by day, sort each group
    days: dict[int | None, list] = {}
    for p in places:
        if not p.get("latitude") or not p.get("longitude"):
            continue
        day = p.get("day_number")
        days.setdefault(day, []).append(p)

    for day_key in days:
        days[day_key].sort(key=lambda x: x.get("order_in_day") or 0)

    # Numbered days first, then unassigned
    sorted_keys = sorted((k for k in days if k is not None), key=int)
    if None in days:
        sorted_keys.append(None)

    for day_key in sorted_keys:
        folder = ET.SubElement(document, "Folder")
        folder_name = f"Day {day_key}" if day_key is not None else "Unassigned"
        ET.SubElement(folder, "name").text = folder_name

        for p in days[day_key]:
            placemark = ET.SubElement(folder, "Placemark")
            ET.SubElement(placemark, "name").text = p.get("name", "")

            desc_parts = [p.get("type", "")]
            if p.get("note"):
                desc_parts.append(p["note"])
            ET.SubElement(placemark, "description").text = " · ".join(desc_parts)

            point = ET.SubElement(placemark, "Point")
            ET.SubElement(point, "coordinates").text = (
                f"{p['longitude']},{p['latitude']},0"
            )

    return ET.tostring(kml, encoding="unicode", xml_declaration=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_export.py -v`
Expected: All PASS (both old and new tests)

- [ ] **Step 5: Add KML download endpoint to export router**

Replace `backend/app/export/router.py` with:

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth.dependencies import get_current_user
from app.maps.export import generate_export_links, generate_kml
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


@router.get("/kml")
async def export_kml(trip_id: str, user: dict = Depends(get_current_user)):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    places = list_places(trip_id)
    trip_name = trip.get("name", "Trip") if isinstance(trip, dict) else getattr(trip, "name", "Trip")
    kml_xml = generate_kml(places, trip_name)

    filename = f"{trip_name}.kml".replace(" ", "_")
    return Response(
        content=kml_xml,
        media_type="application/vnd.google-earth.kml+xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 6: Run all backend tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/maps/export.py backend/app/export/router.py backend/tests/test_export.py
git commit -m "feat: add KML export with per-day folders"
```

---

### Task 4: Frontend — Google Maps Link Utility + API Client Updates

**Files:**
- Modify: `frontend/src/api/client.ts:45-106`
- Modify: `frontend/src/stores/trip.ts`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add `ResolvedPlace` type to types**

In `frontend/src/types/index.ts`, add after `ExportLink`:

```typescript
export interface ResolvedPlace {
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  google_place_id: string;
  formatted_address: string;
}
```

- [ ] **Step 2: Add `resolveGoogleLink` and `exportKml` to API client**

In `frontend/src/api/client.ts`, add the import for `ResolvedPlace` on line 1:

```typescript
import type { User, Trip, Place, ExtractedPlace, DaySchedule, ExportLink, ResolvedPlace } from "../types";
```

Add these two methods to the `api` object, after `exportGoogleMaps`:

```typescript
  resolveGoogleLink: (tripId: string, url: string) =>
    request<ResolvedPlace>(`/trips/${tripId}/places/resolve-google-link`, {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  exportKml: async (tripId: string): Promise<Blob> => {
    const token = localStorage.getItem("token");
    const resp = await fetch(`/api/trips/${tripId}/export/kml`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    return resp.blob();
  },
```

- [ ] **Step 3: Add `resolveGoogleLink` to Zustand store**

In `frontend/src/stores/trip.ts`, add import for `ResolvedPlace`:

```typescript
import type { Trip, Place, ExtractedPlace, ExportLink, ResolvedPlace } from "../types";
```

Add to the `TripState` interface:

```typescript
  resolveGoogleLink: (tripId: string, url: string) => Promise<ResolvedPlace>;
```

Add the implementation in the store, after `exportGoogleMaps`:

```typescript
  resolveGoogleLink: async (tripId, url) => {
    return api.resolveGoogleLink(tripId, url);
  },
```

- [ ] **Step 4: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/stores/trip.ts
git commit -m "feat: add resolveGoogleLink and exportKml to frontend API layer"
```

---

### Task 5: Frontend — Google Maps Link Utility Function

**Files:**
- Create: `frontend/src/utils/googleMapsLink.ts`

- [ ] **Step 1: Create the utility**

Create `frontend/src/utils/googleMapsLink.ts`:

```typescript
import type { Place } from "../types";

export function getGoogleMapsUrl(place: Place): string | null {
  if (place.google_place_id) {
    return `https://www.google.com/maps/place/?q=place_id:${place.google_place_id}`;
  }
  if (place.latitude != null && place.longitude != null) {
    return `https://www.google.com/maps/search/?api=1&query=${place.latitude},${place.longitude}`;
  }
  return null;
}
```

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/googleMapsLink.ts
git commit -m "feat: add Google Maps link utility function"
```

---

### Task 6: Frontend — Editable Place Cards + Google Maps Links (TripDetailPage)

**Files:**
- Modify: `frontend/src/pages/TripDetailPage.tsx`

- [ ] **Step 1: Add editing state, Google Maps links, and updatePlace to TripDetailPage**

Replace the full content of `frontend/src/pages/TripDetailPage.tsx` with:

```typescript
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTripStore } from "../stores/trip";
import { ImageUploader } from "../components/ImageUploader";
import { PlaceForm } from "../components/PlaceForm";
import { ExtractionModal } from "../components/ExtractionModal";
import { getGoogleMapsUrl } from "../utils/googleMapsLink";
import type { ExtractedPlace, Place } from "../types";

function PlaceCard({
  place,
  onDelete,
  onUpdate,
}: {
  place: Place;
  onDelete: () => void;
  onUpdate: (data: { name: string; type: string; note: string }) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(place.name);
  const [type, setType] = useState(place.type);
  const [note, setNote] = useState(place.note);

  const googleMapsUrl = getGoogleMapsUrl(place);
  const TYPES = ["attraction", "restaurant", "hotel", "other"] as const;

  const handleSave = () => {
    onUpdate({ name, type, note });
    setEditing(false);
  };

  const handleCancel = () => {
    setName(place.name);
    setType(place.type);
    setNote(place.note);
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="border rounded-lg p-3 space-y-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border rounded px-2 py-1 text-sm"
        />
        <div className="flex gap-1">
          {TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setType(t)}
              className={`px-2 py-0.5 rounded text-xs border ${
                type === t
                  ? "bg-blue-100 text-blue-700 border-blue-300"
                  : "bg-white text-gray-600 border-gray-200"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          className="w-full border rounded px-2 py-1 text-sm h-12 resize-none"
        />
        <div className="flex gap-2 justify-end">
          <button
            onClick={handleCancel}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Save
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border rounded-lg p-3 flex justify-between items-start">
      <div>
        <div className="font-medium text-sm text-gray-800">{place.name}</div>
        <div className="text-xs text-gray-500 mt-1">
          {place.type}
          {place.note && ` · ${place.note}`}
        </div>
        <div className="text-xs text-gray-400 mt-1">
          Source: {place.source}
        </div>
        {googleMapsUrl && (
          <a
            href={googleMapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:text-blue-700 mt-1 inline-flex items-center gap-1"
          >
            Google Maps &#8599;
          </a>
        )}
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => setEditing(true)}
          className="text-gray-400 hover:text-blue-600 text-sm"
        >
          Edit
        </button>
        <button
          onClick={onDelete}
          className="text-red-400 hover:text-red-600 text-sm"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

export function TripDetailPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const {
    currentTrip,
    places,
    loading,
    fetchTripDetail,
    addPlace,
    updatePlace,
    deletePlace,
    extractPlaces,
  } = useTripStore();
  const [extracting, setExtracting] = useState(false);
  const [extracted, setExtracted] = useState<ExtractedPlace[] | null>(null);

  useEffect(() => {
    if (tripId) fetchTripDetail(tripId);
  }, [tripId, fetchTripDetail]);

  const handleExtract = async (files: File[]) => {
    if (!tripId) return;
    setExtracting(true);
    try {
      const result = await extractPlaces(tripId, files);
      setExtracted(result);
    } finally {
      setExtracting(false);
    }
  };

  const handleConfirmExtracted = async (selected: ExtractedPlace[]) => {
    if (!tripId) return;
    for (const place of selected) {
      await addPlace(tripId, {
        name: place.name,
        type: place.type,
        note: "",
        name_local: place.name_local || "",
        name_en: place.name_en || "",
        latitude: place.latitude,
        longitude: place.longitude,
        day_number: place.day_number,
        order_in_day: place.order_in_day,
        source: "ai_extracted",
      });
    }
    setExtracted(null);
  };

  const handleAddManual = async (data: { name: string; type: string; note: string }) => {
    if (tripId) await addPlace(tripId, data);
  };

  const handleDeletePlace = async (placeId: string) => {
    if (tripId) await deletePlace(tripId, placeId);
  };

  const handleUpdatePlace = async (placeId: string, data: { name: string; type: string; note: string }) => {
    if (tripId) await updatePlace(tripId, placeId, data);
  };

  if (loading || !currentTrip) {
    return <div className="text-center py-20 text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">{currentTrip.name}</h2>
          <p className="text-sm text-gray-500">
            {currentTrip.start_date} ~ {currentTrip.end_date}
          </p>
        </div>
        <Link
          to={`/trips/${tripId}/plan`}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
        >
          Plan Itinerary
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Upload & Add */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-gray-700 mb-3">Upload Screenshots</h3>
            <ImageUploader onUpload={handleExtract} loading={extracting} />
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-gray-700 mb-3">Add Place</h3>
            <PlaceForm onSubmit={handleAddManual} />
          </div>
        </div>

        {/* Right: Place list */}
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h3 className="font-medium text-gray-700 mb-3">
            Places ({places.length})
          </h3>
          <div className="space-y-2">
            {places.map((place) => (
              <PlaceCard
                key={place.id}
                place={place}
                onDelete={() => handleDeletePlace(place.id)}
                onUpdate={(data) => handleUpdatePlace(place.id, data)}
              />
            ))}
            {places.length === 0 && (
              <p className="text-gray-400 text-sm text-center py-8">
                No places yet. Upload screenshots or add manually.
              </p>
            )}
          </div>
        </div>
      </div>

      {extracted && (
        <ExtractionModal
          places={extracted}
          onConfirm={handleConfirmExtracted}
          onClose={() => setExtracted(null)}
        />
      )}
    </div>
  );
}
```

Note: `PlaceForm` currently doesn't accept `tripId` — Task 7 will update both PlaceForm (to accept it) and this file (to pass it).

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TripDetailPage.tsx
git commit -m "feat: editable place cards with Google Maps links on TripDetailPage"
```

---

### Task 7: Frontend — PlaceForm with Google Maps URL Input

**Files:**
- Modify: `frontend/src/components/PlaceForm.tsx`

- [ ] **Step 1: Rewrite PlaceForm with URL input + manual fallback**

Replace `frontend/src/components/PlaceForm.tsx` with:

```typescript
import { useState } from "react";
import { useTripStore } from "../stores/trip";

interface Props {
  onSubmit: (data: { name: string; type: string; note: string; latitude?: number | null; longitude?: number | null; google_place_id?: string; source?: string }) => void;
  tripId: string;
}

const TYPES = ["attraction", "restaurant", "hotel", "other"];

export function PlaceForm({ onSubmit, tripId }: Props) {
  const { resolveGoogleLink } = useTripStore();
  const [mode, setMode] = useState<"url" | "manual">("url");
  const [url, setUrl] = useState("");
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Manual fields
  const [name, setName] = useState("");
  const [type, setType] = useState("attraction");
  const [note, setNote] = useState("");

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setResolving(true);
    setError(null);
    try {
      const resolved = await resolveGoogleLink(tripId, url.trim());
      onSubmit({
        name: resolved.name,
        type: resolved.type,
        note: resolved.formatted_address || "",
        latitude: resolved.latitude,
        longitude: resolved.longitude,
        google_place_id: resolved.google_place_id,
        source: "manual",
      });
      setUrl("");
    } catch {
      setError("Could not resolve this link. Try a different URL or add manually.");
    } finally {
      setResolving(false);
    }
  };

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ name, type, note });
    setName("");
    setNote("");
  };

  return (
    <div className="space-y-3">
      {mode === "url" ? (
        <form onSubmit={handleUrlSubmit} className="border rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Google Maps Link</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://maps.app.goo.gl/..."
              className="w-full border rounded px-3 py-2 text-sm"
              required
            />
          </div>
          {error && <p className="text-red-500 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={resolving}
            className="w-full border border-blue-600 text-blue-600 py-2 rounded-lg text-sm hover:bg-blue-50 disabled:opacity-50"
          >
            {resolving ? "Resolving..." : "+ Add from Link"}
          </button>
          <button
            type="button"
            onClick={() => setMode("manual")}
            className="w-full text-gray-400 text-xs hover:text-gray-600"
          >
            Or add manually
          </button>
        </form>
      ) : (
        <form onSubmit={handleManualSubmit} className="border rounded-lg p-4 space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Place Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g. Senso-ji Temple"
              className="w-full border rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Type</label>
            <div className="flex gap-2">
              {TYPES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={`px-3 py-1 rounded text-xs border ${
                    type === t
                      ? "bg-blue-100 text-blue-700 border-blue-300"
                      : "bg-white text-gray-600 border-gray-200"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Note</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Go early morning to avoid crowds"
              className="w-full border rounded px-3 py-2 text-sm h-16 resize-none"
            />
          </div>
          <button
            type="submit"
            className="w-full border border-blue-600 text-blue-600 py-2 rounded-lg text-sm hover:bg-blue-50"
          >
            + Add Place
          </button>
          <button
            type="button"
            onClick={() => setMode("url")}
            className="w-full text-gray-400 text-xs hover:text-gray-600"
          >
            Or add from Google Maps link
          </button>
        </form>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Update TripDetailPage to pass `tripId` to PlaceForm and accept extended data**

In `frontend/src/pages/TripDetailPage.tsx`, make two changes:

Change `handleAddManual`:
```typescript
  const handleAddManual = async (data: { name: string; type: string; note: string; latitude?: number | null; longitude?: number | null; google_place_id?: string; source?: string }) => {
    if (tripId) await addPlace(tripId, data);
  };
```

Change the PlaceForm JSX to pass `tripId`:
```typescript
            <PlaceForm onSubmit={handleAddManual} tripId={tripId!} />
```

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/PlaceForm.tsx frontend/src/pages/TripDetailPage.tsx
git commit -m "feat: add Google Maps URL input to PlaceForm with manual fallback"
```

---

### Task 8: Frontend — Google Maps Link in InfoWindow + KML Export

**Files:**
- Modify: `frontend/src/components/TripMap.tsx`
- Modify: `frontend/src/pages/PlannerPage.tsx`

- [ ] **Step 1: Add Google Maps link to InfoWindow in TripMap**

In `frontend/src/components/TripMap.tsx`, add import at the top (after the existing imports):

```typescript
import { getGoogleMapsUrl } from "../utils/googleMapsLink";
```

Replace the InfoWindow JSX block (lines 125-141) with:

```typescript
      {selectedPlace && selectedPlace.latitude && selectedPlace.longitude && (
        <InfoWindow
          position={{ lat: selectedPlace.latitude, lng: selectedPlace.longitude }}
          onCloseClick={() => setSelectedPlace(null)}
        >
          <div style={{ padding: "4px 8px" }}>
            <div style={{ fontWeight: 600, fontSize: 14 }}>{selectedPlace.name}</div>
            <div style={{ fontSize: 12, color: "#888", marginTop: 2 }}>
              {selectedPlace.type}
              {selectedPlace.day_number != null ? ` · Day ${selectedPlace.day_number}` : ""}
            </div>
            {selectedPlace.note && (
              <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>{selectedPlace.note}</div>
            )}
            {(() => {
              const url = getGoogleMapsUrl(selectedPlace);
              return url ? (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 12, color: "#2563eb", marginTop: 6, display: "inline-block" }}
                >
                  Open in Google Maps &#8599;
                </a>
              ) : null;
            })()}
          </div>
        </InfoWindow>
      )}
```

- [ ] **Step 2: Replace export modal with KML download in PlannerPage**

Replace the full content of `frontend/src/pages/PlannerPage.tsx` with:

```typescript
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { DragDropContext, type DropResult } from "@hello-pangea/dnd";
import { useTripStore } from "../stores/trip";
import { DayGroup } from "../components/DayGroup";
import { TripMap } from "../components/TripMap";
import { PlanPromptModal } from "../components/PlanPromptModal";
import { api } from "../api/client";
import type { Place } from "../types";

const GOOGLE_MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "";

export function PlannerPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const {
    currentTrip,
    places,
    loading,
    fetchTripDetail,
    updatePlace,
    planTrip,
  } = useTripStore();
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [selectedPlaceId, setSelectedPlaceId] = useState<string | null>(null);

  useEffect(() => {
    if (tripId) fetchTripDetail(tripId);
  }, [tripId, fetchTripDetail]);

  const numDays =
    currentTrip
      ? Math.ceil(
          (new Date(currentTrip.end_date).getTime() -
            new Date(currentTrip.start_date).getTime()) /
            86400000
        ) + 1
      : 0;

  // Group places by day
  const dayGroups: Map<number | null, Place[]> = new Map();
  places.forEach((p) => {
    const day = p.day_number;
    if (!dayGroups.has(day)) dayGroups.set(day, []);
    dayGroups.get(day)!.push(p);
  });

  // Sort within each day
  dayGroups.forEach((group) => {
    group.sort((a, b) => a.order_in_day - b.order_in_day);
  });

  const handleDragEnd = async (result: DropResult) => {
    if (!result.destination || !tripId) return;

    const placeId = result.draggableId;
    const destDay = result.destination.droppableId === "unassigned"
      ? null
      : parseInt(result.destination.droppableId.replace("day-", ""));
    const destIndex = result.destination.index;

    await updatePlace(tripId, placeId, {
      day_number: destDay,
      order_in_day: destIndex + 1,
    });
  };

  const handlePlan = async (prompt: string) => {
    if (!tripId) return;
    setPlanning(true);
    setPlanError(null);
    try {
      await planTrip(tripId, prompt);
      setShowPlanModal(false);
    } catch {
      setPlanError("Planning failed. Please try again.");
    } finally {
      setPlanning(false);
    }
  };

  const handleExportKml = async () => {
    if (!tripId) return;
    try {
      const blob = await api.exportKml(tripId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${currentTrip?.name || "trip"}.kml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("KML export failed:", e);
    }
  };

  if (loading || !currentTrip) {
    return <div className="text-center py-20 text-gray-500">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <Link to={`/trips/${tripId}`} className="text-gray-400 hover:text-gray-600">
            &larr;
          </Link>
          <h2 className="text-xl font-bold text-gray-800">
            {currentTrip.name} — Itinerary
          </h2>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowPlanModal(true)}
            className="bg-white border border-blue-600 text-blue-600 px-4 py-2 rounded-lg text-sm hover:bg-blue-50"
          >
            AI Plan
          </button>
          <button
            onClick={handleExportKml}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
          >
            Export KML
          </button>
        </div>
      </div>

      <div className="flex gap-4" style={{ height: "calc(100vh - 160px)" }}>
        {/* Left: Itinerary */}
        <div className="w-80 overflow-y-auto flex-shrink-0">
          <DragDropContext onDragEnd={handleDragEnd}>
            {Array.from({ length: numDays }, (_, i) => i + 1).map((day) => (
              <DayGroup
                key={day}
                dayNumber={day}
                places={dayGroups.get(day) || []}
                label={`Day ${day}`}
                onPlaceClick={(p) => setSelectedPlaceId(p.id)}
              />
            ))}
            <DayGroup
              dayNumber={null}
              places={dayGroups.get(null) || []}
              label="Unassigned"
              onPlaceClick={(p) => setSelectedPlaceId(p.id)}
            />
          </DragDropContext>
        </div>

        {/* Right: Map */}
        <div className="flex-1 bg-white rounded-lg shadow-sm overflow-hidden">
          <TripMap places={places} googleMapsApiKey={GOOGLE_MAPS_KEY} selectedPlaceId={selectedPlaceId} />
        </div>
      </div>

      {showPlanModal && (
        <PlanPromptModal
          onSubmit={handlePlan}
          onClose={() => setShowPlanModal(false)}
          loading={planning}
          error={planError}
        />
      )}
    </div>
  );
}
```

Key changes from original:
- Removed `exportGoogleMaps` from store destructuring
- Removed `exportLinks` state and the export links modal
- Added `handleExportKml` using `api.exportKml` + blob download
- Button text changed to "Export KML"
- Added `import { api } from "../api/client"` for direct KML fetch

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 4: Run ESLint**

Run: `cd frontend && npm run lint`
Expected: No errors (warnings OK)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/TripMap.tsx frontend/src/pages/PlannerPage.tsx
git commit -m "feat: Google Maps link in InfoWindow + KML export replacing directions URL"
```

---

### Task 9: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All PASS

- [ ] **Step 2: Verify frontend builds clean**

Run: `cd frontend && npm run build`
Expected: PASS with no TypeScript errors

- [ ] **Step 3: Run frontend linter**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 4: Verify no type inconsistencies**

Check that:
- `PlaceForm` props include `tripId: string` — ✓ (Task 7)
- `TripDetailPage` passes `tripId={tripId!}` to `PlaceForm` — ✓ (Task 7)
- `handleAddManual` in TripDetailPage accepts extended data shape — ✓ (Task 7)
- `ResolvedPlace` type matches backend response — ✓ (Task 4)
- `api.exportKml` returns `Blob` — ✓ (Task 4)
- `getGoogleMapsUrl` imported correctly in both TripMap and TripDetailPage — ✓ (Tasks 5, 6, 8)
