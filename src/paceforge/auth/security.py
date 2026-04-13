"""Password hashing and JWT token management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 30
_REFRESH_EXPIRE_DAYS = 30


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
        expires_delta or timedelta(minutes=_ACCESS_EXPIRE_MINUTES)
    )
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def create_refresh_token(
    user_id: str,
    secret: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(days=_REFRESH_EXPIRE_DAYS)
    )
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    """Decode and verify a JWT. Returns ``{"sub": ..., "role": ...}``.

    Raises ``jwt.ExpiredSignatureError`` or ``jwt.InvalidTokenError``
    on failure.
    """
    payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    if payload.get("type") == "refresh":
        raise jwt.InvalidTokenError("Cannot use refresh token as access token")
    return payload


def decode_refresh_token(token: str, secret: str) -> dict:
    """Decode and verify a refresh token. Returns ``{"sub": ...}``.

    Raises ``jwt.ExpiredSignatureError`` or ``jwt.InvalidTokenError``
    on failure.
    """
    payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Not a refresh token")
    return payload
