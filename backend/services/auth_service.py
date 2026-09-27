import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from backend.models import User
from backend.database import async_session

_JWT_SECRET = None
_JWT_SECRET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".jwt_secret")

def _get_jwt_secret() -> str:
    global _JWT_SECRET
    if _JWT_SECRET is not None:
        return _JWT_SECRET
    if os.path.exists(_JWT_SECRET_FILE):
        with open(_JWT_SECRET_FILE) as f:
            _JWT_SECRET = f.read().strip()
    else:
        _JWT_SECRET = os.environ.get("JWT_SECRET", str(uuid.uuid4()))
        try:
            with open(_JWT_SECRET_FILE, "w") as f:
                f.write(_JWT_SECRET)
        except OSError:
            pass
    return _JWT_SECRET

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))


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


async def register_user(first_name: str) -> User:
    """Create a new user with a display ID. Subscription remains 'free' until mock payment."""
    async with async_session() as session:
        display_id = await _next_display_id()
        user = User(
            id=str(uuid.uuid4()),
            display_id=display_id,
            first_name=first_name,
            subscription_status="free",
        )
        session.add(user)
        await session.commit()
        return user


async def activate_subscription(user_id: str) -> User | None:
    """Mock payment — mark user's subscription as active for 30 days."""
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.subscription_status = "active"
        user.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await session.commit()
        return user


async def login_by_display_id(display_id: int, first_name: str) -> User | None:
    """Look up user by display ID and verify first name matches."""
    from sqlalchemy import select
    async with async_session() as session:
        stmt = select(User).where(User.display_id == display_id).where(User.first_name == first_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def is_subscription_active(user: User) -> bool:
    """Check if the user's subscription is currently active."""
    if user.subscription_status != "active":
        return False
    if user.subscription_expires_at and user.subscription_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        # Subscription expired — update status
        async with async_session() as session:
            u = await session.get(User, user.id)
            if u:
                u.subscription_status = "expired"
                await session.commit()
        return False
    return True