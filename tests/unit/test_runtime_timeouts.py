import asyncio

import pytest

from src.company.runtime import RuntimeTimeoutController


@pytest.mark.asyncio
async def test_operation_completes_before_timeout() -> None:
    controller = RuntimeTimeoutController(timeout_seconds=0.1)

    async def operation() -> None:
        await asyncio.sleep(0.01)

    result = await controller.execute(operation)

    assert result.completed is True
    assert result.timed_out is False
    assert result.duration_seconds >= 0


@pytest.mark.asyncio
async def test_operation_times_out() -> None:
    controller = RuntimeTimeoutController(timeout_seconds=0.01)

    async def operation() -> None:
        await asyncio.sleep(0.1)

    result = await controller.execute(operation)

    assert result.completed is False
    assert result.timed_out is True
    assert result.duration_seconds >= 0.01


@pytest.mark.asyncio
async def test_timeout_cancels_operation() -> None:
    controller = RuntimeTimeoutController(timeout_seconds=0.01)
    cancelled = False

    async def operation() -> None:
        nonlocal cancelled
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            cancelled = True
            raise

    result = await controller.execute(operation)

    assert result.timed_out is True
    assert cancelled is True


def test_invalid_timeout_is_rejected() -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        RuntimeTimeoutController(timeout_seconds=0)

    with pytest.raises(ValueError, match="timeout_seconds"):
        RuntimeTimeoutController(timeout_seconds=-1)
