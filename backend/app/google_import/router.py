import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.google_import.parser import parse_csv, compute_trip_center, filter_nearby
from app.google_import.smart_insert import assign_to_days
from app.maps.geocoding import geocode_places
from app.places import repository as places_repo
from app.places.models import PlaceResponse
from app.trips.repository import get_trip

router = APIRouter(prefix="/api/trips/{trip_id}/google-import", tags=["google-import"])

ALLOWED_CSV_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel"}


class ConfirmPlace(BaseModel):
    title: str
    note: str = ""
    url: str = ""


class ConfirmRequest(BaseModel):
    places: list[ConfirmPlace]


def _verify_trip_access(trip_id: str, user: dict):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.post("/preview")
async def preview(
    trip_id: str,
    files: list[UploadFile],
    user: dict = Depends(get_current_user),
):
    _verify_trip_access(trip_id, user)

    # Validate files
    for f in files:
        filename = f.filename or ""
        if f.content_type not in ALLOWED_CSV_TYPES and not filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {filename}. Only CSV files are accepted.",
            )

    # Parse CSVs
    all_lists: dict[str, list[dict]] = {}
    for f in files:
        content = await f.read()
        list_name = os.path.splitext(f.filename or "unknown")[0]
        parsed = parse_csv(content, list_name)
        if list_name in all_lists:
            all_lists[list_name].extend(parsed)
        else:
            all_lists[list_name] = parsed

    # Get existing trip places and compute center
    existing = places_repo.list_places(trip_id)
    center = compute_trip_center(existing)

    # Filter nearby if we have a center
    trip_center = None
    if center:
        trip_center = {"lat": center[0], "lon": center[1]}
        for places in all_lists.values():
            filter_nearby(places, center[0], center[1])

    lists = [{"name": name, "places": places} for name, places in all_lists.items()]

    return {"lists": lists, "trip_center": trip_center}


@router.post("/confirm")
async def confirm(
    trip_id: str,
    body: ConfirmRequest,
    user: dict = Depends(get_current_user),
):
    trip = _verify_trip_access(trip_id, user)

    if not body.places:
        raise HTTPException(status_code=400, detail="No places to import")

    # Geocode selected places (pass trip's country_code for better accuracy)
    geocode_input = [{"name": p.title, "note": p.note} for p in body.places]
    country_code = trip.get("country_code")
    geocoded = await geocode_places(geocode_input, country_code=country_code)

    # Get existing trip places for smart insert
    existing = places_repo.list_places(trip_id)

    # Build place dicts with geocoded coordinates
    new_places = []
    for i, p in enumerate(body.places):
        geo = geocoded[i]
        new_places.append({
            "name": p.title,
            "type": "google_saved",
            "note": p.note,
            "google_maps_url": p.url,
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "google_place_id": geo.get("google_place_id"),
            "geocode_confidence": geo.get("geocode_confidence"),
            "source": "google_import",
        })

    # Smart insert: assign day_number and order_in_day
    assign_to_days(new_places, existing)

    # Create places in database
    imported = []
    for np in new_places:
        doc = places_repo.create_place(trip_id, np, source="google_import")
        imported.append(doc)

    return {"imported": imported}
