from datetime import datetime

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: str
    trip_id: str
    blob_url: str
    uploaded_at: datetime
