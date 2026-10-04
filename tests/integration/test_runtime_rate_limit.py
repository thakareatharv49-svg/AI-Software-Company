from __future__ import annotations

import asyncio

import pytest

from company.runtime.rate_limit import (
    RateLimitedRuntime,
    RuntimeRateLimiter,
    RuntimeRateLimitError,
)


class FakeRuntime:
    async def execute(self, operation):
        return await operation()


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit() -> None:
    limiter = RuntimeRateLimiter(limit=2)

    assert await limiter.acquire() is True
    assert await limiter.acquire() is True

    state = await limiter.state()

    assert state.current == 2
    assert state.limit == 2
    assert state.allowed is False
    assert state.rejected == 0


@pytest.mark.asyncio
async def test_rate_limiter_rejects_above_limit() -> None:
    limiter = RuntimeRateLimiter(limit=1)

    assert await limiter.acquire() is True
    assert await limiter.acquire() is False

    state = await limiter.state()

    assert state.current == 1
    assert state.rejected == 1


@pytest.mark.asyncio
async def test_release_restores_capacity() -> None:
    limiter = RuntimeRateLimiter(limit=1)

    assert await limiter.acquire() is True
    await limiter.release()

    assert await limiter.acquire() is True

    state = await limiter.state()

    assert state.current == 1


@pytest.mark.asyncio
async def test_reset_clears_state() -> None:
    limiter = RuntimeRateLimiter(limit=1)

    await limiter.acquire()
    await limiter.acquire()

    await limiter.reset()

    state = await limiter.state()

    assert state.current == 0
    assert state.rejected == 0
    assert state.allowed is True


@pytest.mark.asyncio
async def test_rate_limited_runtime_releases_after_success() -> None:
    limiter = RuntimeRateLimiter(limit=1)
    runtime = RateLimitedRuntime(FakeRuntime(), limiter)

    async def operation():
        return "success"

    result = await runtime.execute(operation)

    assert result == "success"

    state = await limiter.state()

    assert state.current == 0


@pytest.mark.asyncio
async def test_rate_limited_runtime_releases_after_failure() -> None:
    limiter = RuntimeRateLimiter(limit=1)
    runtime = RateLimitedRuntime(FakeRuntime(), limiter)

    async def operation():
        raise RuntimeError("failure")

    with pytest.raises(RuntimeError, match="failure"):
        await runtime.execute(operation)

    state = await limiter.state()

    assert state.current == 0


@pytest.mark.asyncio
async def test_rate_limited_runtime_rejects_when_busy() -> None:
    limiter = RuntimeRateLimiter(limit=1)
    runtime = RateLimitedRuntime(FakeRuntime(), limiter)

    started = asyncio.Event()
    release = asyncio.Event()

    async def operation():
        started.set()
        await release.wait()
        return "success"

    first = asyncio.create_task(runtime.execute(operation))

    await started.wait()

    with pytest.raises(
        RuntimeRateLimitError,
        match="rate limit exceeded",
    ):
        await runtime.execute(operation)

    release.set()

    assert await first == "success"

    state = await limiter.state()

    assert state.current == 0
    assert state.rejected == 1


def test_invalid_rate_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        RuntimeRateLimiter(limit=0)
