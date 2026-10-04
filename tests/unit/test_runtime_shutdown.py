import asyncio

import pytest

from src.company.runtime import RuntimeShutdownController


@pytest.mark.asyncio
async def test_shutdown_request_completes_when_no_tasks_are_active() -> None:
    async def active_tasks() -> int:
        return 0

    controller = RuntimeShutdownController(active_tasks)

    state = await controller.request_shutdown()

    assert state.requested is True
    assert state.completed is True
    assert state.active_tasks == 0


@pytest.mark.asyncio
async def test_shutdown_waits_when_tasks_are_active() -> None:
    active = 1

    async def active_tasks() -> int:
        return active

    controller = RuntimeShutdownController(active_tasks)

    state = await controller.request_shutdown()

    assert state.requested is True
    assert state.completed is False
    assert state.active_tasks == 1

    active = 0

    completed = await controller.complete()

    assert completed.requested is True
    assert completed.completed is True
    assert completed.active_tasks == 0


@pytest.mark.asyncio
async def test_shutdown_request_can_be_observed() -> None:
    async def active_tasks() -> int:
        return 0

    controller = RuntimeShutdownController(active_tasks)

    waiter = asyncio.create_task(controller.wait_for_request())

    await asyncio.sleep(0)
    assert waiter.done() is False

    await controller.request_shutdown()

    await asyncio.wait_for(waiter, timeout=1)


@pytest.mark.asyncio
async def test_shutdown_completion_can_be_observed() -> None:
    async def active_tasks() -> int:
        return 0

    controller = RuntimeShutdownController(active_tasks)

    await controller.complete()
    await asyncio.wait_for(
        controller.wait_until_complete(),
        timeout=1,
    )

    state = await controller.status()

    assert state.requested is True
    assert state.completed is True
    assert state.active_tasks == 0


@pytest.mark.asyncio
async def test_status_reports_current_active_tasks() -> None:
    active = 2

    async def active_tasks() -> int:
        return active

    controller = RuntimeShutdownController(active_tasks)

    state = await controller.status()

    assert state.requested is False
    assert state.completed is False
    assert state.active_tasks == 2


@pytest.mark.asyncio
async def test_complete_sets_shutdown_request() -> None:
    async def active_tasks() -> int:
        return 3

    controller = RuntimeShutdownController(active_tasks)

    state = await controller.complete()

    assert state.requested is True
    assert state.completed is True
    assert state.active_tasks == 3
