from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.schemas import error_detail
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


@dataclass
class YouTubeAccess:
    """Why YouTube access was granted, and what it costs.

    Richer than require_subscriber's bare User so the handler can tell a paid
    subscriber from a trial user without re-running the check: `is_trial` is what
    decides whether a free-trial use must be charged for this request.
    """
    user: User
    is_trial: bool
    trial_uses_remaining: int | None


async def require_youtube_access(
    current_user: User | None = Depends(get_current_user),
) -> YouTubeAccess:
    """FastAPI dependency: admits a paid subscriber OR a trial account.

    Deliberately a *sibling* of require_subscriber rather than a wrapper: a trial
    user's subscription_status is "free", which require_subscriber rejects with 402
    before any trial logic could run.

    Branches on the boolean returned by is_subscription_active, never on
    current_user.subscription_status: that helper flips an expired subscription to
    "expired" in a *separate* session, so the object passed in here is stale.

    This decides *who* gets in, not *how much they have left*. An account with 0 uses
    remaining is admitted on purpose: the quota is enforced at consume time by
    trial_service.decrement_trial_use, which is the only place that can tell a
    genuinely new job from a duplicate. Rejecting here would lock a user out of a
    result they had already paid for, and out of reading their own past jobs.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if await is_subscription_active(current_user):
        return YouTubeAccess(
            user=current_user,
            is_trial=False,
            trial_uses_remaining=current_user.trial_uses_remaining,
        )

    remaining = current_user.trial_uses_remaining

    # NULL means this account was never granted a trial (as opposed to 0, which means
    # "used up"). The two states drive different UI and only the NULL case is refused
    # here, because there is no consume that could ever succeed for it.
    if remaining is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=error_detail(
                "subscription_required",
                "An active subscription is required for YouTube analysis.",
                trial_uses_remaining=None,
            ),
        )

    return YouTubeAccess(user=current_user, is_trial=True, trial_uses_remaining=remaining)
