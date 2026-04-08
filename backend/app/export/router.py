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
