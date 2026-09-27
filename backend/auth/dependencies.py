from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.services.auth_service import decode_access_token, get_user_by_id, is_subscription_active
from backend.models import User

_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> User | None:
    """FastAPI dependency: extracts and validates JWT, returns the User or None.
    Unlike the old version, this is OPTIONAL — returns None if no token provided.
    Used by public endpoints that want to identify the user if logged in."""
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    return await get_user_by_id(user_id)


async def require_subscriber(
    current_user: User | None = Depends(get_current_user),
) -> User:
    """FastAPI dependency: requires a valid JWT + active subscription.
    Raises 401/403 if missing/expired/invalid."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not await is_subscription_active(current_user):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required. Please subscribe at /subscribe",
        )

    return current_user