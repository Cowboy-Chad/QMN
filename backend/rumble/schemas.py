from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime


class RumbleRequest(BaseModel):
    url: str = ""
    pattern: str


class JobStatusResponse(BaseModel):
    id: str
    source: str
    url: Optional[str] = None
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    pattern: str
    status: str
    transcript: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            return dt.isoformat() + "+00:00"
        return dt.isoformat()