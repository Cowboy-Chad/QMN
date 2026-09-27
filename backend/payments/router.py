from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.services.auth_service import activate_subscription
from backend.models import User

router = APIRouter(prefix="/api/payments")


class MockSubscribeResponse(BaseModel):
    success: bool
    message: str
    subscription_status: str
    subscription_expires_at: str | None = None


@router.post("/mock-subscribe", response_model=MockSubscribeResponse)
async def mock_subscribe(current_user: User | None = Depends(get_current_user)):
    """Mock PayPal subscription — activates a 30-day subscription for the current user.
    No real payment involved. Used for local testing and development."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="You must register first before subscribing")

    user = await activate_subscription(current_user.id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    expires = user.subscription_expires_at.isoformat() if user.subscription_expires_at else None

    return MockSubscribeResponse(
        success=True,
        message=f"Subscription activated! Welcome, {user.first_name}. Your subscription is active until {expires}.",
        subscription_status=user.subscription_status,
        subscription_expires_at=expires,
    )