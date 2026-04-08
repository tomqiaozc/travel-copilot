# Google Maps Platform Migration — Design Spec

## Goal

Replace all Azure Maps dependencies with Google Maps Platform. No backward compatibility.

## Changes

### 1. Backend: Geocoding (backend/app/maps/geocoding.py)

Replace Azure Maps Fuzzy Search with Google Geocoding API.

**Google Geocoding API endpoint:** `https://maps.googleapis.com/maps/api/geocode/json`
- Parameters: `address` (query string), `key` (API key), `region` (country bias), `language`
- Response structure: `results[].geometry.location.{lat, lng}`, `results[].place_id`, `results[].formatted_address`

**Changes to geocoding.py:**
- `_azure_maps_search()` → `_google_geocode()`: Call Google Geocoding API instead of Azure Maps Fuzzy Search. Return list of results with `{lat, lng, place_id}`.
- `_pick_best()`: Adapt to Google's response format (`geometry.location.lat/lng` instead of `position.lat/lon`). Return `{latitude, longitude, google_place_id}`.
- `geocode_place()`: Return dict now includes `google_place_id` alongside lat/lng.
- `_reverse_geocode_city()`: Use Google Reverse Geocoding (`latlng` parameter) instead of Azure Maps reverse.
- `_validate_result()`: Adapt to Google's response structure.
- All existing logic (multi-strategy parallel search, cluster validation, outlier detection) is preserved — only the HTTP calls and response parsing change.

### 2. Backend: Config (backend/app/config.py)

- Add `google_maps_api_key: str = ""` to Settings
- `azure_maps_key` can remain but will no longer be used

### 3. Backend: Data Model (backend/app/places/models.py)

- Add `google_place_id: Optional[str] = None` to `PlaceCreate`, `PlaceUpdate`, `PlaceResponse`

### 4. Backend: Export (backend/app/maps/export.py)

- `generate_google_maps_url()`: When places have `google_place_id`, use `https://www.google.com/maps/place/?q=place_id:ChIJ...` format. Fall back to coordinate-based URLs.
- For directions URLs with multiple places, use `place_id:` waypoints when available.

### 5. Backend: AI Extract Router (backend/app/ai/router.py)

- After geocoding, store `google_place_id` in each place's data (it comes from geocode_place result).

### 6. Frontend: Map Component (frontend/src/components/TripMap.tsx)

Complete rewrite using `@vis.gl/react-google-maps`:
- Remove `azure-maps-control` import
- Use `<Map>`, `<AdvancedMarker>`, `<InfoWindow>` from `@vis.gl/react-google-maps`
- Preserve all current features: color-coded day markers, route polylines, click popup, fly-to-selected, day legend
- Props change: `azureMapsKey` → `googleMapsApiKey`

### 7. Frontend: PlannerPage (frontend/src/pages/PlannerPage.tsx)

- `AZURE_MAPS_KEY` → `GOOGLE_MAPS_KEY` using `VITE_GOOGLE_MAPS_API_KEY`
- Update TripMap prop name

### 8. Frontend: Types (frontend/src/types/index.ts)

- Add `google_place_id?: string` to `Place` and `ExtractedPlace`

### 9. Frontend: Dependencies

- `npm uninstall azure-maps-control`
- `npm install @vis.gl/react-google-maps`

### 10. Tests

**Backend tests to update:**
- `test_maps.py`: Update mock to match Google Geocoding API response format
- `test_export.py`: Add tests for place_id-based URLs
- `test_e2e.py`: Update "Azure Maps" references to "Google Maps"

**Integration tests to update:**
- `tests/test_geocoding.py`: Update to use Google Geocoding API

### 11. Cleanup

- Remove `VITE_AZURE_MAPS_KEY` from frontend .env
- Remove `azure-maps-control` from package.json
- No need to remove `azure_maps_key` from backend config (harmless)
