import asyncio

import pytest

from src.company.runtime import (
    BackpressuredRuntimeExecutor,
    RuntimeBackpressureController,
)


@pytest.mark.asyncio
async def test_controller_allows_capacity() -> None:
    controller = RuntimeBackpressureController(max_tasks=2)

    first = await controller.acquire()
    second = await controller.acquire()

    assert first.allowed is True
    assert second.allowed is True
    assert second.active_tasks == 2


@pytest.mark.asyncio
async def test_controller_blocks_when_capacity_is_full() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)

    await controller.acquire()
    blocked = await controller.acquire()

    assert blocked.allowed is False
    assert blocked.active_tasks == 1
    assert blocked.max_tasks == 1


@pytest.mark.asyncio
async def test_release_restores_capacity() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)

    await controller.acquire()
    await controller.release()

    status = await controller.status()

    assert status.allowed is True
    assert status.active_tasks == 0


@pytest.mark.asyncio
async def test_release_does_not_go_below_zero() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)

    await controller.release()
    status = await controller.status()

    assert status.active_tasks == 0


@pytest.mark.asyncio
async def test_invalid_capacity_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_tasks"):
        RuntimeBackpressureController(max_tasks=0)


@pytest.mark.asyncio
async def test_executor_runs_when_capacity_exists() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)

    async def operation() -> str:
        return "success"

    executor = BackpressuredRuntimeExecutor(operation, controller)

    assert await executor.execute() == "success"
    assert (await controller.status()).active_tasks == 0


@pytest.mark.asyncio
async def test_executor_rejects_when_capacity_is_full() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)
    await controller.acquire()

    async def operation() -> str:
        return "should not run"

    executor = BackpressuredRuntimeExecutor(operation, controller)

    with pytest.raises(RuntimeError, match="capacity exceeded"):
        await executor.execute()


@pytest.mark.asyncio
async def test_executor_releases_capacity_after_failure() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)

    async def operation() -> None:
        raise RuntimeError("operation failed")

    executor = BackpressuredRuntimeExecutor(operation, controller)

    with pytest.raises(RuntimeError, match="operation failed"):
        await executor.execute()

    assert (await controller.status()).active_tasks == 0


@pytest.mark.asyncio
async def test_concurrent_execution_respects_capacity() -> None:
    controller = RuntimeBackpressureController(max_tasks=1)
    started = 0
    finished = 0

    async def operation() -> str:
        nonlocal started, finished
        started += 1
        await asyncio.sleep(0.01)
        finished += 1
        return "done"

    executor = BackpressuredRuntimeExecutor(operation, controller)

    results = await asyncio.gather(
        executor.execute(),
        executor.execute(),
        return_exceptions=True,
    )

    assert results.count("done") == 1
    assert sum(isinstance(result, RuntimeError) for result in results) == 1
    assert started == 1
    assert finished == 1
    assert (await controller.status()).active_tasks == 0
