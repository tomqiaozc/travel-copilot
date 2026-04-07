from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.auth.dependencies import get_current_user
from app.images import repository
from app.trips.repository import get_trip

router = APIRouter(prefix="/api/trips/{trip_id}/images", tags=["images"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_images(
    trip_id: str,
    images: list[UploadFile],
    user: dict = Depends(get_current_user),
):
    trip = get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")

    if len(images) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images allowed")

    results = []
    for image in images:
        data = await image.read()
        doc = repository.upload_image(
            trip_id=trip_id,
            filename=image.filename or "image.png",
            data=data,
            content_type=image.content_type or "image/png",
        )
        results.append(doc)
    return results
