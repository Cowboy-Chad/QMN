from pydantic import BaseModel, field_serializer, ConfigDict
from typing import Optional
from datetime import datetime


def error_detail(code: str, message: str, **extra) -> dict:
    """Structured HTTPException detail so the frontend can branch on `code`
    instead of printing a raw JSON body. Serializes as
    {"detail": {"code": ..., "message": ..., **extra}}."""
    return {"code": code, "message": message, **extra}


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


# ── Auth schemas (email + password for YouTube accounts; Rumble needs no account) ──

class RegisterRequest(BaseModel):
    """Create a YouTube account. Every new account is granted the free trial."""
    full_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    """Login with email + password."""
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    # from_attributes lets one helper build this from a User row instead of three
    # hand-written copies. Only the fields declared here are serialized, so
    # password_hash is never exposed.
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_id: Optional[int] = None
    first_name: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    subscription_status: str = "free"
    subscription_expires_at: Optional[datetime] = None
    # NULL = no trial on this account; 0 = trial exhausted. The frontend needs the
    # distinction to choose between "subscribe" and "your trial is used up".
    trial_uses_remaining: Optional[int] = None
    created_at: datetime

    @field_serializer("created_at", "subscription_expires_at")
    def serialize_dt(self, dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.isoformat() + "+00:00"
        return dt.isoformat()