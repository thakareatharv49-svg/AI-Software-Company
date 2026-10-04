import asyncio

import pytest

from src.company.runtime import RuntimeLifecycle


@pytest.mark.asyncio
async def test_lifecycle_starts() -> None:
    lifecycle = RuntimeLifecycle()

    assert lifecycle.running is False

    await lifecycle.start()

    assert lifecycle.running is True


@pytest.mark.asyncio
async def test_task_can_be_registered_after_start() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    task = asyncio.create_task(asyncio.sleep(60))

    try:
        await lifecycle.register_task(task)

        assert await lifecycle.active_tasks() == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_task_registration_requires_running_runtime() -> None:
    lifecycle = RuntimeLifecycle()
    task = asyncio.create_task(asyncio.sleep(60))

    try:
        with pytest.raises(
            RuntimeError,
            match="not running",
        ):
            await lifecycle.register_task(task)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_stop_cancels_active_tasks() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    task = asyncio.create_task(asyncio.sleep(60))
    await lifecycle.register_task(task)

    result = await lifecycle.stop()

    assert result.stopped is True
    assert result.cancelled_tasks == 1
    assert lifecycle.running is False
    assert await lifecycle.active_tasks() == 0
    assert task.cancelled() is True


@pytest.mark.asyncio
async def test_stop_is_safe_without_tasks() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    result = await lifecycle.stop()

    assert result.stopped is True
    assert result.cancelled_tasks == 0
    assert lifecycle.running is False


@pytest.mark.asyncio
async def test_invalid_shutdown_timeout_is_rejected() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    with pytest.raises(
        ValueError,
        match="greater than 0",
    ):
        await lifecycle.stop(0)


@pytest.mark.asyncio
async def test_completed_task_is_removed_from_registry() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    async def operation() -> None:
        await asyncio.sleep(0)

    task = asyncio.create_task(operation())
    await lifecycle.register_task(task)
    await task

    await asyncio.sleep(0)

    assert await lifecycle.active_tasks() == 0
