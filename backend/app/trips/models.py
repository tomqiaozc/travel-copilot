from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    country_code: Optional[str] = None


class TripUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    country_code: Optional[str] = None


class TripResponse(BaseModel):
    id: str
    user_id: str
    name: str
    start_date: date
    end_date: date
    country_code: Optional[str] = None
    created_at: datetime
