# Place Cards Enhancement + KML Export — Design Spec

## Goal

Two features: (1) Enhanced place cards with editing, Google Maps links, and add-by-link. (2) KML file export replacing the current directions URL export.

---

## Feature 1: Place Cards Enhancement

### 1.1 Editable Place Cards (TripDetailPage)

Currently, saved places on `/trips/:tripId` are read-only cards with only a delete button. AI-extracted and manual places should both support inline editing.

**UI changes to TripDetailPage place cards:**
- Each card gets an "Edit" button alongside the existing "Delete" button
- Edit mode: name (text input), type (select dropdown), note (textarea) become editable inline
- Save/Cancel buttons replace Edit/Delete in edit mode
- On save: call `updatePlace(tripId, placeId, {name, type, note})` via the store

**No new components** — edit mode is toggled state within the existing card `<div>` in TripDetailPage.

### 1.2 Google Maps Link on Every Place

Every place card (TripDetailPage) and map InfoWindow (PlannerPage) shows a clickable Google Maps link.

**Link generation logic (frontend utility):**
- If `google_place_id` exists: `https://www.google.com/maps/place/?q=place_id:{google_place_id}`
- Else if `latitude` and `longitude` exist: `https://www.google.com/maps/search/?api=1&query={lat},{lng}`
- Else: no link shown

**TripDetailPage cards:** Add link icon + "Google Maps" text below the source line, opens in new tab.

**PlannerPage InfoWindow:** Add "在 Google Maps 中打开" link at the bottom of the popup.

### 1.3 Add Place via Google Maps Link

Replace the current manual PlaceForm (name + type + note fields) with a URL-based input for adding places.

**Frontend UI (TripDetailPage):**
- Primary input: a text field for pasting Google Maps URLs + "Add" button
- Accepts: `https://maps.app.goo.gl/xxx` (short links) and `https://www.google.com/maps/place/...` (full URLs)
- Loading spinner while resolving
- On success: place is auto-added to the trip (calls `addPlace`)
- Below the URL input: a small "Or add manually" toggle that shows the existing PlaceForm fields (name, type, note) as fallback

**Backend endpoint: `POST /api/trips/{trip_id}/places/resolve-google-link`**

Input:
```json
{"url": "https://maps.app.goo.gl/xxx"}
```

Processing steps:
1. Follow HTTP redirects on the URL using `httpx` (async) to get the full Google Maps URL
2. Parse the resolved URL to extract either:
   - `place_id` from the URL path/data parameters
   - Or coordinates/place name from the URL
3. If `place_id` found: call Google Place Details API (Pro tier fields: `displayName`, `location`, `primaryType`, `formattedAddress`, `googleMapsUri`)
4. If only name/coordinates: call Google Geocoding API to get `place_id`, then Place Details
5. Map Google's `primaryType` to our type system:
   - `restaurant`, `cafe`, `bakery`, `bar`, etc. → `"restaurant"`
   - `lodging`, `hotel`, `motel`, etc. → `"hotel"`
   - `tourist_attraction`, `museum`, `park`, `temple`, etc. → `"attraction"`
   - Everything else → `"other"`
6. Return resolved place data

Output:
```json
{
  "name": "北野異人館",
  "type": "attraction",
  "latitude": 34.6983,
  "longitude": 135.1911,
  "google_place_id": "ChIJxxx",
  "formatted_address": "..."
}
```

Error cases:
- Invalid URL (not a Google Maps link): 400 with message
- Redirect fails / URL cannot be resolved: 400 with message
- Place not found in Google APIs: 404 with message

**New file:** `backend/app/maps/place_resolver.py` — contains the resolution logic (URL parsing, redirect following, Place Details API call, type mapping). Router stays in `backend/app/places/router.py`.

### 1.4 Bug Fix: `google_place_id` Not Persisted

`backend/app/places/repository.py` `create_place()` (line 22-35) does not include `google_place_id` in the document. Add it:
```python
"google_place_id": data.get("google_place_id"),
```

### 1.5 PlaceUpdate Model: Add Coordinates

`backend/app/places/models.py` `PlaceUpdate` currently omits `latitude` and `longitude`. Add them as optional fields so that places added via link resolution (or re-resolved) can have their coordinates updated.

---

## Feature 2: KML Export

Replace the current per-day Google Maps directions URL export with a downloadable KML file.

### 2.1 Backend: KML Generation

**Modify:** `backend/app/maps/export.py`

Add `generate_kml(places: list, trip_name: str) -> str`:
- Group places by `day_number`, sort each day by `order_in_day`
- Generate KML XML with structure:
  ```xml
  <?xml version="1.0" encoding="UTF-8"?>
  <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
      <name>{trip_name}</name>
      <Folder>
        <name>Day 1</name>
        <Placemark>
          <name>北野異人館</name>
          <description>attraction · 值得一看的西洋建筑群</description>
          <Point>
            <coordinates>135.1911,34.6983,0</coordinates>
          </Point>
        </Placemark>
        ...
      </Folder>
      <Folder>
        <name>Day 2</name>
        ...
      </Folder>
      <Folder>
        <name>Unassigned</name>
        ...
      </Folder>
    </Document>
  </kml>
  ```
- Places without coordinates are skipped
- Unassigned places (`day_number` is null) go into an "Unassigned" folder (only if any exist)
- Use `xml.etree.ElementTree` from stdlib — no new dependencies

**Keep** `generate_google_maps_url()` and `generate_export_links()` — they may still be useful. Don't remove.

### 2.2 Backend: KML Download Endpoint

**Modify:** `backend/app/export/router.py`

Add `GET /api/trips/{trip_id}/export/kml`:
- Verify trip ownership
- Fetch trip (for name) and all places
- Call `generate_kml(places, trip.name)`
- Return `Response(content=kml_xml, media_type="application/vnd.google-earth.kml+xml")` with `Content-Disposition: attachment; filename="{trip_name}.kml"`

### 2.3 Frontend: KML Download Button

**Modify:** `frontend/src/pages/PlannerPage.tsx`

- Change "Export to Google Maps" button to "Export KML"
- On click: fetch `/api/trips/{tripId}/export/kml`, create blob, trigger browser download
- Remove the export links modal (no longer needed)
- Remove `exportGoogleMaps` from the store (replaced by direct fetch + download)

### 2.4 Frontend: API Client + Store

- Add `exportKml(tripId)` to `api/client.ts` — returns raw `Response` (not JSON) for blob download
- Remove or keep `exportGoogleMaps` in store (keep for backward compatibility, but UI no longer calls it)

---

## Data Model Changes

### Backend `PlaceUpdate` (models.py)
```python
class PlaceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    note: Optional[str] = None
    name_local: Optional[str] = None
    name_en: Optional[str] = None
    latitude: Optional[float] = None      # NEW
    longitude: Optional[float] = None     # NEW
    google_place_id: Optional[str] = None
    day_number: Optional[int] = None
    order_in_day: Optional[int] = None
```

### Backend `repository.py` `create_place()`
Add `"google_place_id": data.get("google_place_id")` to the document dict.

### Frontend types — no changes needed
`Place` already has `google_place_id?: string`.

---

## New Files

| File | Purpose |
|------|---------|
| `backend/app/maps/place_resolver.py` | Google Maps URL resolution: redirect following, URL parsing, Place Details API call, type mapping |

## Modified Files

| File | Changes |
|------|---------|
| `backend/app/places/models.py` | Add `latitude`, `longitude` to `PlaceUpdate` |
| `backend/app/places/repository.py` | Add `google_place_id` to `create_place` doc |
| `backend/app/places/router.py` | Add `POST /trips/{trip_id}/places/resolve-google-link` endpoint |
| `backend/app/maps/export.py` | Add `generate_kml()` function |
| `backend/app/export/router.py` | Add `GET /export/kml` endpoint |
| `frontend/src/pages/TripDetailPage.tsx` | Editable place cards, Google Maps links, URL-based add place |
| `frontend/src/pages/PlannerPage.tsx` | KML export button, Google Maps link in InfoWindow |
| `frontend/src/components/TripMap.tsx` | Add Google Maps link to InfoWindow |
| `frontend/src/components/PlaceForm.tsx` | Add URL input mode with manual fallback |
| `frontend/src/api/client.ts` | Add `resolveGoogleLink()`, `exportKml()` |
| `frontend/src/stores/trip.ts` | Add `resolveGoogleLink` action |

---

## Tests

**Backend:**
- `test_export.py`: Add test for `generate_kml()` — verify XML structure, day grouping, coordinate format
- `test_place_resolver.py` (new): Test URL parsing, type mapping, mock Place Details API call
- `test_maps.py`: Verify `google_place_id` persistence in create flow

**Frontend:**
- Manual testing: edit place, add via link, KML download, InfoWindow link
