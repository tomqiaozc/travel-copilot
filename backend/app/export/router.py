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
