"""Cryptographic primitives for opaque, server-side browser sessions.

Only the SHA-256 digest belongs in the database. The raw token is returned once
for delivery in an HttpOnly cookie and must never be logged or persisted.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta


DEFAULT_SESSION_TTL = timedelta(days=7)
MAX_SESSION_TTL = timedelta(days=30)


def issue_session_token() -> tuple[str, str]:
    """Return (raw_token, token_hash); persist only token_hash."""
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_session_token(raw_token)


def hash_session_token(raw_token: str) -> str:
    """Return a fixed-length digest suitable for the auth_sessions table."""
    if not isinstance(raw_token, str) or not raw_token:
        raise ValueError("Session token must be a non-empty string")
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def session_expiry(
    *,
    now: datetime | None = None,
    ttl: timedelta = DEFAULT_SESSION_TTL,
) -> datetime:
    """Return a timezone-aware UTC expiry, rejecting unsafe TTL values."""
    if ttl <= timedelta(0) or ttl > MAX_SESSION_TTL:
        raise ValueError("Session TTL must be greater than zero and at most 30 days")
    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("Session creation time must be timezone-aware")
    return current.astimezone(UTC) + ttl
