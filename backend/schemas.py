from pydantic import BaseModel, field_serializer
from typing import Optional
from datetime import datetime


class JobStatusResponse(BaseModel):
    id: str
    source: str
    video_url: Optional[str] = None
    video_id: Optional[str] = None
    channel_id: Optional[str] = None
    channel_title: Optional[str] = None
    video_title: Optional[str] = None
    analyst_name: Optional[str] = "Anonymous"
    analyst_display_id: Optional[int] = None
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


# ── Auth schemas (simplified — no passwords, no emails) ──

class RegisterRequest(BaseModel):
    """Register with just a first name. Subscription activated after mock payment."""
    first_name: str


class LoginRequest(BaseModel):
    """Login with display ID + first name."""
    display_id: int
    first_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    display_id: Optional[int] = None
    first_name: str
    subscription_status: str = "free"
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime

    @field_serializer("created_at", "subscription_expires_at")
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.isoformat() + "+00:00"
        return dt.isoformat()