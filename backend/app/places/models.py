from typing import Optional

from pydantic import BaseModel, Field


class PlaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern="^(attraction|restaurant|hotel|other)$")
    note: str = ""
    name_local: Optional[str] = None
    name_en: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    day_number: Optional[int] = None
    order_in_day: Optional[int] = None
    source: Optional[str] = None


class PlaceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    note: Optional[str] = None
    name_local: Optional[str] = None
    name_en: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    day_number: Optional[int] = None
    order_in_day: Optional[int] = None


class PlaceResponse(BaseModel):
    id: str
    trip_id: str
    name: str
    type: str
    note: str
    name_local: Optional[str] = None
    name_en: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    source: str
    day_number: Optional[int] = None
    order_in_day: int
