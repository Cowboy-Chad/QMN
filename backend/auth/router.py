from fastapi import APIRouter, HTTPException, Depends

from backend.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from backend.services.auth_service import (
    register_user, login_by_display_id, create_access_token,
    activate_subscription,
)
from backend.auth.dependencies import get_current_user
from backend.models import User

router = APIRouter(prefix="/api/auth")


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    """Register with just a first name. Subscription is 'free' until mock payment."""
    first_name = body.first_name.strip()
    if len(first_name) < 1:
        raise HTTPException(status_code=400, detail="First name is required")
    if len(first_name) > 50:
        raise HTTPException(status_code=400, detail="First name too long (max 50 characters)")

    user = await register_user(first_name)

    token = create_access_token({"sub": user.id, "first_name": user.first_name, "display_id": user.display_id})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            display_id=user.display_id,
            first_name=user.first_name,
            subscription_status=user.subscription_status,
            subscription_expires_at=user.subscription_expires_at,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login with display ID + first name."""
    user = await login_by_display_id(body.display_id, body.first_name.strip())
    if user is None:
        raise HTTPException(status_code=401, detail="User not found. Check your ID and name.")

    token = create_access_token({"sub": user.id, "first_name": user.first_name, "display_id": user.display_id})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            display_id=user.display_id,
            first_name=user.first_name,
            subscription_status=user.subscription_status,
            subscription_expires_at=user.subscription_expires_at,
            created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User | None = Depends(get_current_user)):
    """Return current user info, or 401 if not authenticated."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse(
        id=current_user.id,
        display_id=current_user.display_id,
        first_name=current_user.first_name,
        subscription_status=current_user.subscription_status,
        subscription_expires_at=current_user.subscription_expires_at,
        created_at=current_user.created_at,
    )