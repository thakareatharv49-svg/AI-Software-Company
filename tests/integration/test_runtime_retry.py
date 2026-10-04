from __future__ import annotations

import pytest

from company.runtime.retry import (
    RuntimeRetryController,
    RuntimeRetryPolicy,
)


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures() -> None:
    controller = RuntimeRetryController(
        RuntimeRetryPolicy(max_attempts=3)
    )

    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise RuntimeError("temporary failure")

    result = await controller.execute(operation)

    assert result.attempts == 3
    assert result.succeeded is True
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_stops_after_max_attempts() -> None:
    controller = RuntimeRetryController(
        RuntimeRetryPolicy(max_attempts=2)
    )

    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        await controller.execute(operation)

    assert attempts == 2


def test_retry_policy_exponential_backoff() -> None:
    policy = RuntimeRetryPolicy(
        max_attempts=5,
        base_delay_seconds=1.0,
        max_delay_seconds=10.0,
    )

    assert policy.delay_for(1) == 1.0
    assert policy.delay_for(2) == 2.0
    assert policy.delay_for(3) == 4.0
    assert policy.delay_for(4) == 8.0
    assert policy.delay_for(5) == 10.0


def test_retry_policy_caps_backoff() -> None:
    policy = RuntimeRetryPolicy(
        max_attempts=10,
        base_delay_seconds=5.0,
        max_delay_seconds=7.0,
    )

    assert policy.delay_for(1) == 5.0
    assert policy.delay_for(2) == 7.0
    assert policy.delay_for(10) == 7.0


def test_invalid_retry_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        RuntimeRetryPolicy(max_attempts=0)

    with pytest.raises(ValueError):
        RuntimeRetryPolicy(base_delay_seconds=-1)

    with pytest.raises(ValueError):
        RuntimeRetryPolicy(max_delay_seconds=-1)

    with pytest.raises(ValueError):
        RuntimeRetryPolicy(
            base_delay_seconds=5,
            max_delay_seconds=2,
        )


def test_invalid_attempt_number_is_rejected() -> None:
    policy = RuntimeRetryPolicy()

    with pytest.raises(ValueError):
        policy.delay_for(0)
