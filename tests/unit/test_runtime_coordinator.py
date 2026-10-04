import asyncio

import pytest

from src.company.runtime import RuntimeCoordinator


@pytest.mark.asyncio
async def test_runtime_must_be_started_before_execution() -> None:
    runtime = RuntimeCoordinator()

    async def operation() -> str:
        return "ok"

    with pytest.raises(
        RuntimeError,
        match="not running",
    ):
        await runtime.execute(operation)


@pytest.mark.asyncio
async def test_runtime_executes_operation() -> None:
    runtime = RuntimeCoordinator()
    await runtime.start()

    async def operation() -> str:
        return "success"

    result = await runtime.execute(operation)

    assert result == "success"

    status = await runtime.status()
    assert status.running is True
    assert status.active_runs == 0


@pytest.mark.asyncio
async def test_runtime_limits_concurrent_operations() -> None:
    runtime = RuntimeCoordinator(max_concurrent_runs=1)
    await runtime.start()

    active = 0
    maximum_active = 0

    async def operation() -> None:
        nonlocal active, maximum_active

        active += 1
        maximum_active = max(maximum_active, active)

        await asyncio.sleep(0.02)

        active -= 1

    await asyncio.gather(
        runtime.execute(operation),
        runtime.execute(operation),
        runtime.execute(operation),
    )

    assert maximum_active == 1


@pytest.mark.asyncio
async def test_runtime_releases_slot_after_failure() -> None:
    runtime = RuntimeCoordinator(max_concurrent_runs=1)
    await runtime.start()

    async def failing_operation() -> None:
        raise RuntimeError("failure")

    with pytest.raises(RuntimeError, match="failure"):
        await runtime.execute(failing_operation)

    status = await runtime.status()
    assert status.active_runs == 0

    async def successful_operation() -> str:
        return "recovered"

    assert await runtime.execute(successful_operation) == "recovered"


@pytest.mark.asyncio
async def test_runtime_stop_prevents_new_operations() -> None:
    runtime = RuntimeCoordinator()
    await runtime.start()
    await runtime.stop()

    async def operation() -> str:
        return "ok"

    with pytest.raises(RuntimeError, match="not running"):
        await runtime.execute(operation)


@pytest.mark.asyncio
async def test_runtime_tracks_active_runs() -> None:
    runtime = RuntimeCoordinator(max_concurrent_runs=2)
    await runtime.start()

    started = asyncio.Event()
    release = asyncio.Event()

    async def operation() -> str:
        started.set()
        await release.wait()
        return "done"

    first = asyncio.create_task(runtime.execute(operation))
    second = asyncio.create_task(runtime.execute(operation))

    await started.wait()
    await asyncio.sleep(0.01)

    status = await runtime.status()
    assert status.active_runs == 2
    assert status.max_concurrent_runs == 2

    release.set()

    assert await first == "done"
    assert await second == "done"
