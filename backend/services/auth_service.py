import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError as JWTError

from backend.models import User
from backend.database import async_session

_JWT_SECRET = None
_JWT_SECRET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".jwt_secret")


def _get_jwt_secret() -> str:
    """The HMAC signing key.

    The ENVIRONMENT WINS over the file. That order is load-bearing in production:
    Render supplies JWT_SECRET as a generated env var, and if a stale
    backend/.jwt_secret ever found its way into the image, file-first precedence
    would silently override the managed secret. Env-first also means no secret is
    ever written to disk in a container, whose filesystem is wiped on every deploy.

    The file remains the local-development convenience it always was: generated
    once, gitignored, stable across restarts.
    """
    global _JWT_SECRET
    if _JWT_SECRET is not None:
        return _JWT_SECRET

    env_secret = os.environ.get("JWT_SECRET")
    if env_secret:
        _JWT_SECRET = env_secret
        return _JWT_SECRET  # never write a file when the environment supplies it

    if os.path.exists(_JWT_SECRET_FILE):
        with open(_JWT_SECRET_FILE) as f:
            _JWT_SECRET = f.read().strip()
    else:
        _JWT_SECRET = str(uuid.uuid4())
        try:
            with open(_JWT_SECRET_FILE, "w") as f:
                f.write(_JWT_SECRET)
        except OSError:
            pass  # read-only filesystem — the in-memory secret still serves this process
    return _JWT_SECRET


def assert_jwt_secret_configured() -> None:
    """Refuse to start in production without an explicit JWT_SECRET.

    Without this the app mints a fresh random secret on every container start,
    which invalidates every issued token on every deploy — and looks like an
    unexplained mass logout rather than a misconfiguration.
    """
    if os.environ.get("RENDER") and not os.environ.get("JWT_SECRET"):
        raise RuntimeError(
            "JWT_SECRET must be set in production (Render generates one; "
            "the file fallback is for local development only)."
        )

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))

# Free-trial allowance granted to every new account at signup.
TRIAL_USE_LIMIT = 33


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def _next_display_id() -> int:
    """Get the next available display ID (auto-incrementing integer)."""
    from sqlalchemy import select, func
    try:
        async with async_session() as session:
            result = await session.execute(select(func.max(User.display_id)))
            max_id = result.scalar()
            return (max_id or 0) + 1
    except Exception:
        # Table may not exist yet on first run
        return 1


async def get_user_by_id(user_id: str) -> User | None:
    async with async_session() as session:
        return await session.get(User, user_id)


def _first_name_from(full_name: str) -> str:
    """The users.first_name column is NOT NULL and drives the nav bar
    ("Sarah (#7)") and analyst attribution. Derive it from the first token of
    the full name so every existing display path keeps working."""
    return full_name.split()[0][:50]


async def register_user(full_name: str, email: str, password: str) -> User | None:
    """Create a YouTube account. Returns None if the email is already registered.

    `email` must already be normalized (lowercased) by the caller.
    Every account is granted TRIAL_USE_LIMIT free analyses, whether or not the
    user goes on to subscribe — so a lapsed subscriber is not worse off than a
    new one.
    """
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from backend.services.password_service import hash_password

    password_hash = hash_password(password)
    first_name = _first_name_from(full_name)

    # display_id comes from its own session, so two concurrent signups can compute
    # the same id. The pre-check gives a clean answer in the common case; the
    # IntegrityError catch below is the backstop, retrying only on a display_id
    # collision and reporting "taken" for an email collision.
    for _ in range(3):
        async with async_session() as session:
            existing = await session.execute(select(User.id).where(User.email == email))
            if existing.first() is not None:
                return None
            user = User(
                id=str(uuid.uuid4()),
                display_id=await _next_display_id(),
                first_name=first_name,
                full_name=full_name,
                email=email,
                password_hash=password_hash,
                subscription_status="free",
                trial_uses_remaining=TRIAL_USE_LIMIT,
            )
            session.add(user)
            try:
                await session.commit()
                return user
            except IntegrityError as e:
                await session.rollback()
                # Prefer the driver's constraint name. Matching on the raw error
                # text only worked by accident — it happened to contain the index
                # name `ix_users_email` — and would break silently if that index
                # were ever renamed.
                constraint = getattr(getattr(e, "orig", None), "constraint_name", None)
                detail = str(constraint) if constraint else str(e)
                if "email" in detail.lower():
                    return None  # a real duplicate
                continue  # display_id collision — recompute and retry

    raise RuntimeError("Could not allocate a display id after 3 attempts")


async def activate_subscription(user_id: str) -> User | None:
    """Mock payment — mark user's subscription as active for 30 days.

    Deliberately leaves trial_uses_remaining untouched: subscribing must not
    consume the trial, and a lapsed subscriber keeps whatever was left.
    """
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.subscription_status = "active"
        user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await session.commit()
        return user


async def login_by_email(email: str, password: str) -> User | None:
    """Look up by email and verify the password.

    Returns None for BOTH "no such email" and "wrong password" so the endpoint
    cannot be used to enumerate which emails have accounts.
    """
    from sqlalchemy import select
    from backend.services.password_service import verify_password

    async with async_session() as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


async def get_trial_uses_remaining(user_id: str) -> int | None:
    """Remaining free-trial analyses, or None if this account has no trial."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        return user.trial_uses_remaining if user else None


async def is_subscription_active(user: User) -> bool:
    """Check if the user's subscription is currently active."""
    if user.subscription_status != "active":
        return False
    # subscription_expires_at is timestamptz, so the value read back is aware and
    # compares directly against an aware `now`. (This used to strip tzinfo off
    # `now` to match a naive SQLite read; with timezone-aware columns that would
    # raise TypeError -> a 500 on every /api/auth/me for an active subscriber.)
    if user.subscription_expires_at and user.subscription_expires_at < datetime.now(timezone.utc):
        # Subscription expired — update status
        async with async_session() as session:
            u = await session.get(User, user.id)
            if u:
                u.subscription_status = "expired"
                await session.commit()
        return False
    return True