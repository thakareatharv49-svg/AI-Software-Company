import pytest

from src.company.runtime import RuntimeResourceMonitor


@pytest.mark.asyncio
async def test_initial_resource_state() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=4)

    state = await monitor.snapshot()

    assert state.active_tasks == 0
    assert state.max_tasks == 4
    assert state.utilization_percent == 0
    assert state.available_capacity == 4


@pytest.mark.asyncio
async def test_increment_updates_utilization() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=4)

    state = await monitor.increment()
    assert state.active_tasks == 1
    assert state.utilization_percent == 25
    assert state.available_capacity == 3

    state = await monitor.increment()
    assert state.active_tasks == 2
    assert state.utilization_percent == 50
    assert state.available_capacity == 2


@pytest.mark.asyncio
async def test_decrement_releases_capacity() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=2)

    await monitor.increment()
    await monitor.increment()

    state = await monitor.decrement()

    assert state.active_tasks == 1
    assert state.utilization_percent == 50
    assert state.available_capacity == 1


@pytest.mark.asyncio
async def test_increment_does_not_exceed_capacity() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=1)

    await monitor.increment()
    state = await monitor.increment()

    assert state.active_tasks == 1
    assert state.available_capacity == 0
    assert state.utilization_percent == 100


@pytest.mark.asyncio
async def test_decrement_does_not_go_below_zero() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=1)

    state = await monitor.decrement()

    assert state.active_tasks == 0
    assert state.available_capacity == 1


@pytest.mark.asyncio
async def test_set_active_tasks() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=5)

    state = await monitor.set_active_tasks(3)

    assert state.active_tasks == 3
    assert state.max_tasks == 5
    assert state.utilization_percent == 60
    assert state.available_capacity == 2


@pytest.mark.asyncio
async def test_invalid_active_tasks_are_rejected() -> None:
    monitor = RuntimeResourceMonitor(max_tasks=2)

    with pytest.raises(ValueError, match="active_tasks"):
        await monitor.set_active_tasks(-1)


def test_invalid_max_tasks_are_rejected() -> None:
    with pytest.raises(ValueError, match="max_tasks"):
        RuntimeResourceMonitor(max_tasks=0)
