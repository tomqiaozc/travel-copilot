from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.places.models import PlaceCreate, PlaceUpdate, ReorderRequest
from app.places import repository
from app.trips.repository import get_trip
from app.maps.place_resolver import resolve_google_maps_link
from app.maps.opening_hours import fetch_opening_hours_batch

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
    doc = repository.create_place(trip_id, body.model_dump(), source=body.source or "manual")
    if doc.get("google_place_id") and not doc.get("opening_hours"):
        hours = await fetch_opening_hours_batch([doc])
        if hours[0]:
            repository.update_place(doc["id"], trip_id, {"opening_hours": hours[0]})
            doc["opening_hours"] = hours[0]
    return doc


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def create_places_batch(
    trip_id: str, body: list[PlaceCreate], user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    docs = []
    need_hours = []
    for item in body:
        doc = repository.create_place(trip_id, item.model_dump(), source=item.source or "manual")
        docs.append(doc)
        if doc.get("google_place_id") and not doc.get("opening_hours"):
            need_hours.append(doc)
    if need_hours:
        hours = await fetch_opening_hours_batch(need_hours)
        for doc, h in zip(need_hours, hours):
            if h:
                repository.update_place(doc["id"], trip_id, {"opening_hours": h})
                doc["opening_hours"] = h
    return docs


@router.put("/reorder")
async def reorder_places_endpoint(
    trip_id: str, body: ReorderRequest, user: dict = Depends(get_current_user)
):
    _verify_trip_access(trip_id, user)
    updated = repository.reorder_places(trip_id, [p.model_dump() for p in body.placements])
    return updated


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
