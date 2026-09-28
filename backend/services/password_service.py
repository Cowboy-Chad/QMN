"""Password hashing for YouTube accounts.

Uses bcrypt directly rather than passlib: passlib is effectively unmaintained and
has a known incompatibility with bcrypt 4.x+ (which is present here as 5.0.0).
"""
import bcrypt

# bcrypt silently truncates input beyond 72 BYTES. Two different long passwords
# would then authenticate the same account, so anything longer is rejected
# instead of truncated. Callers validate against this before hashing.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8

# Cost factor. 12 is the conventional default and keeps hashing well under 1s.
_BCRYPT_ROUNDS = 12


def hash_password(raw: str) -> str:
    """Hash a plaintext password. Caller must validate length first."""
    encoded = raw.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password exceeds {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(raw: str, password_hash: str | None) -> bool:
    """Constant-time password check. Returns False (never raises) on a missing or
    malformed stored hash, so a corrupt row cannot 500 the login endpoint."""
    if not raw or not password_hash:
        return False
    try:
        encoded = raw.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False
