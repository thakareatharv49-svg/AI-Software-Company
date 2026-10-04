from __future__ import annotations

import asyncio

import pytest

from company.runtime.cancellation import RuntimeCancellationController


@pytest.mark.asyncio
async def test_operation_completes_without_cancellation() -> None:
    controller = RuntimeCancellationController()

    async def operation():
        return "success"

    result = await controller.execute(operation)

    assert result.completed is True
    assert result.cancelled is False


@pytest.mark.asyncio
async def test_cancellation_stops_running_operation() -> None:
    controller = RuntimeCancellationController()
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def operation():
        started.set()
        try:
            await asyncio.sleep(10)
        finally:
            stopped.set()

    task = asyncio.create_task(controller.execute(operation))

    await started.wait()
    await controller.cancel()

    result = await task

    assert result.cancelled is True
    assert result.completed is False
    assert stopped.is_set()


@pytest.mark.asyncio
async def test_cancel_before_execution_prevents_operation() -> None:
    controller = RuntimeCancellationController()
    called = False

    async def operation():
        nonlocal called
        called = True

    await controller.cancel()

    result = await controller.execute(operation)

    assert result.cancelled is True
    assert result.completed is False
    assert called is False


@pytest.mark.asyncio
async def test_reset_allows_execution_again() -> None:
    controller = RuntimeCancellationController()

    await controller.cancel()
    await controller.reset()

    async def operation():
        return "success"

    result = await controller.execute(operation)

    assert result.completed is True
    assert result.cancelled is False


@pytest.mark.asyncio
async def test_cancelled_operation_does_not_leave_task_running() -> None:
    controller = RuntimeCancellationController()

    async def operation():
        await asyncio.sleep(10)

    task = asyncio.create_task(controller.execute(operation))

    await asyncio.sleep(0)
    await controller.cancel()

    result = await task

    assert result.cancelled is True
    assert result.completed is False
