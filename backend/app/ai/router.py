from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.ai.extract import extract_places_from_images
from app.ai.planner import plan_itinerary
from app.images import repository as image_repo
from app.places.repository import list_places, update_place
from app.maps.geocoding import geocode_places
from app.trips.repository import get_trip, update_trip

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["ai"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}


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

    for image in images:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {image.content_type}")

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
    result = await extract_places_from_images(image_data_list)
    return {
        "places": result["places"],
        "country_code": result.get("country_code"),
    }


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
        country_code = trip.get("country_code")
        geo_results = await geocode_places(
            places=needs_geocoding,
            location_hint=trip.get("name", ""),
            country_code=country_code,
        )
        for place, geo in zip(needs_geocoding, geo_results):
            place["latitude"] = geo["latitude"]
            place["longitude"] = geo["longitude"]
            update_place(place["id"], trip_id, {
                "latitude": geo["latitude"],
                "longitude": geo["longitude"],
            })

    # Calculate number of days from trip dates
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
