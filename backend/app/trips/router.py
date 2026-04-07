from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.trips.models import TripCreate, TripUpdate
from app.trips import repository

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("")
async def list_trips(user: dict = Depends(get_current_user)):
    return repository.list_trips(user["user_id"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trip(body: TripCreate, user: dict = Depends(get_current_user)):
    return repository.create_trip(
        user_id=user["user_id"],
        data=body.model_dump(mode="json"),
    )


@router.get("/{trip_id}")
async def get_trip(trip_id: str, user: dict = Depends(get_current_user)):
    trip = repository.get_trip(trip_id, user["user_id"])
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.put("/{trip_id}")
async def update_trip(trip_id: str, body: TripUpdate, user: dict = Depends(get_current_user)):
    trip = repository.update_trip(
        trip_id, user["user_id"], body.model_dump(exclude_none=True, mode="json")
    )
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(trip_id: str, user: dict = Depends(get_current_user)):
    repository.delete_trip(trip_id, user["user_id"])
