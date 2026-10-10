from datetime import UTC, datetime, timedelta

import pytest

from src.security.session_tokens import (
    DEFAULT_SESSION_TTL,
    hash_session_token,
    issue_session_token,
    session_expiry,
)


def test_issued_token_is_opaque_and_only_hash_is_fixed_length() -> None:
    raw_token, token_hash = issue_session_token()

    assert raw_token
    assert raw_token != token_hash
    assert len(token_hash) == 64
    assert hash_session_token(raw_token) == token_hash


def test_hash_is_deterministic_and_rejects_empty_tokens() -> None:
    assert hash_session_token("example-token") == hash_session_token("example-token")
    with pytest.raises(ValueError):
        hash_session_token("")


def test_expiry_defaults_to_seven_days_and_is_utc() -> None:
    now = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    expiry = session_expiry(now=now)

    assert expiry == now + DEFAULT_SESSION_TTL
    assert expiry.utcoffset() == timedelta(0)


@pytest.mark.parametrize("ttl", [timedelta(0), timedelta(seconds=-1), timedelta(days=31)])
def test_expiry_rejects_invalid_ttl(ttl: timedelta) -> None:
    with pytest.raises(ValueError):
        session_expiry(ttl=ttl)


def test_expiry_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        session_expiry(now=datetime(2026, 10, 10, 10, 0))
