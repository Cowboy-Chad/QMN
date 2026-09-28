import re

from fastapi import APIRouter, HTTPException, Depends

from backend.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse, error_detail,
)
from backend.services.auth_service import (
    register_user, login_by_email, create_access_token,
)
from backend.services.password_service import MIN_PASSWORD_LENGTH, MAX_PASSWORD_BYTES
from backend.auth.dependencies import get_current_user
from backend.models import User

router = APIRouter(prefix="/api/auth")

# Deliberately simple: `EmailStr` would require adding email-validator, which is
# not installed. Validation lives in the router, matching this codebase's style.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(raw: str) -> str:
    """Strip, lowercase and validate. Lowercasing is what makes the unique email
    index effectively case-insensitive, so Trial1@x.com collides with trial1@x.com."""
    email = (raw or "").strip().lower()
    if len(email) < 6 or len(email) > 254 or not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=400,
            detail=error_detail("invalid_email", "Enter a valid email address"),
        )
    return email


def _validate_password(raw: str) -> str:
    if not raw or len(raw) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                "weak_password",
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
            ),
        )
    # bcrypt truncates past 72 bytes, so a longer password would silently make two
    # different passwords equivalent. Reject rather than truncate.
    if len(raw.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=error_detail(
                "password_too_long",
                f"Password must be at most {MAX_PASSWORD_BYTES} bytes",
            ),
        )
    return raw


def _user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def _token_response(user: User) -> TokenResponse:
    token = create_access_token(
        {"sub": user.id, "first_name": user.first_name, "display_id": user.display_id}
    )
    return TokenResponse(access_token=token, user=_user_response(user))


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):
    """Create a YouTube account with full name + email + password.

    Every new account is granted the free trial; subscribing is a separate choice.
    """
    full_name = (body.full_name or "").strip()
    if not full_name:
        raise HTTPException(
            status_code=400, detail=error_detail("invalid_name", "Full name is required")
        )
    if len(full_name) > 100:
        raise HTTPException(
            status_code=400,
            detail=error_detail("invalid_name", "Full name too long (max 100 characters)"),
        )

    email = _normalize_email(body.email)
    password = _validate_password(body.password)

    user = await register_user(full_name, email, password)
    if user is None:
        raise HTTPException(
            status_code=409,
            detail=error_detail(
                "email_taken",
                "That email is already registered. Try logging in instead.",
            ),
        )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login with email + password.

    One message for both failure modes so the endpoint cannot be used to discover
    which emails have accounts.
    """
    email = (body.email or "").strip().lower()
    user = await login_by_email(email, body.password or "")
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=error_detail(
                "bad_credentials", "Incorrect email or password."
            ),
        )
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User | None = Depends(get_current_user)):
    """Return current user info, or 401 if not authenticated."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _user_response(current_user)
