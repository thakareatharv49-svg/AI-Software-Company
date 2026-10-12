from src.security.rate_limit import InMemoryRateLimiter


def test_rate_limiter_blocks_after_limit_and_reports_retry_after() -> None:
    now = [100.0]
    limiter = InMemoryRateLimiter(clock=lambda: now[0])

    assert limiter.check("start:127.0.0.1", limit=2, window_seconds=10).allowed
    assert limiter.check("start:127.0.0.1", limit=2, window_seconds=10).allowed
    blocked = limiter.check("start:127.0.0.1", limit=2, window_seconds=10)

    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 10

    now[0] = 110.1
    assert limiter.check("start:127.0.0.1", limit=2, window_seconds=10).allowed


def test_rate_limiter_separates_clients_and_bounds_key_storage() -> None:
    limiter = InMemoryRateLimiter(max_keys=2, clock=lambda: 1.0)

    assert limiter.check("a", limit=1, window_seconds=60).allowed
    assert limiter.check("b", limit=1, window_seconds=60).allowed
    assert limiter.check("c", limit=1, window_seconds=60).allowed
    assert len(limiter._events) <= 2


def test_rate_limiter_rejects_invalid_limits() -> None:
    import pytest

    limiter = InMemoryRateLimiter()
    with pytest.raises(ValueError):
        limiter.check("client", limit=0, window_seconds=60)
    with pytest.raises(ValueError):
        limiter.check("client", limit=1, window_seconds=0)
