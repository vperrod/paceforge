"""Password hashing and JWT token management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

_ALGORITHM = "HS256"
_DEFAULT_EXPIRE_HOURS = 24


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Check *plain* against a bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    user_id: str,
    role: str,
    secret: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create an HS256-signed JWT with *user_id* and *role* claims."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(hours=_DEFAULT_EXPIRE_HOURS)
    )
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    """Decode and verify a JWT. Returns ``{"sub": ..., "role": ...}``.

    Raises ``jwt.ExpiredSignatureError`` or ``jwt.InvalidTokenError``
    on failure.
    """
    return jwt.decode(token, secret, algorithms=[_ALGORITHM])
