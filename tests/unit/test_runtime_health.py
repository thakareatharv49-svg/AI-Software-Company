import asyncio

import pytest

from src.company.runtime import (
    RuntimeHealthMonitor,
    RuntimeLifecycle,
)


@pytest.mark.asyncio
async def test_health_is_healthy_when_runtime_is_running() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    monitor = RuntimeHealthMonitor(
        max_concurrent_runs=2,
        is_running=lambda: lifecycle.running,
        active_tasks=lifecycle.active_tasks,
    )

    health = await monitor.check()

    assert health.healthy is True
    assert health.running is True
    assert health.active_tasks == 0
    assert health.max_concurrent_runs == 2


@pytest.mark.asyncio
async def test_health_is_unhealthy_when_runtime_is_stopped() -> None:
    lifecycle = RuntimeLifecycle()

    monitor = RuntimeHealthMonitor(
        max_concurrent_runs=2,
        is_running=lambda: lifecycle.running,
        active_tasks=lifecycle.active_tasks,
    )

    health = await monitor.check()

    assert health.healthy is False
    assert health.running is False


@pytest.mark.asyncio
async def test_health_tracks_active_tasks() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    monitor = RuntimeHealthMonitor(
        max_concurrent_runs=2,
        is_running=lambda: lifecycle.running,
        active_tasks=lifecycle.active_tasks,
    )

    task = asyncio.create_task(asyncio.sleep(60))

    try:
        await lifecycle.register_task(task)

        health = await monitor.check()

        assert health.healthy is True
        assert health.active_tasks == 1
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_last_health_is_updated() -> None:
    lifecycle = RuntimeLifecycle()
    await lifecycle.start()

    monitor = RuntimeHealthMonitor(
        max_concurrent_runs=1,
        is_running=lambda: lifecycle.running,
        active_tasks=lifecycle.active_tasks,
    )

    assert monitor.last_health is None

    health = await monitor.check()

    assert monitor.last_health == health


@pytest.mark.asyncio
async def test_health_rejects_invalid_concurrency_limit() -> None:
    lifecycle = RuntimeLifecycle()

    with pytest.raises(
        ValueError,
        match="at least 1",
    ):
        RuntimeHealthMonitor(
            max_concurrent_runs=0,
            is_running=lambda: lifecycle.running,
            active_tasks=lifecycle.active_tasks,
        )
