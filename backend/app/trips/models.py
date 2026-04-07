from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date


class TripUpdate(BaseModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class TripResponse(BaseModel):
    id: str
    user_id: str
    name: str
    start_date: date
    end_date: date
    created_at: datetime
