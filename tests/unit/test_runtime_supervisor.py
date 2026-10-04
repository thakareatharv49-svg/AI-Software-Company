import asyncio

import pytest

from src.company.runtime import RuntimeSupervisor


@pytest.mark.asyncio
async def test_supervisor_starts() -> None:
    async def health_check() -> bool:
        return True

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    await supervisor.start()

    try:
        status = supervisor.status()

        assert status.running is True
    finally:
        await supervisor.stop()


@pytest.mark.asyncio
async def test_supervisor_check_now_records_health() -> None:
    async def health_check() -> bool:
        return True

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    assert await supervisor.check_now() is True

    status = supervisor.status()

    assert status.healthy is True
    assert status.restart_count == 0


@pytest.mark.asyncio
async def test_supervisor_handles_unhealthy_runtime() -> None:
    async def health_check() -> bool:
        return False

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    assert await supervisor.check_now() is False

    status = supervisor.status()

    assert status.healthy is False


@pytest.mark.asyncio
async def test_supervisor_handles_health_check_exception() -> None:
    async def health_check() -> bool:
        raise RuntimeError("health failure")

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    assert await supervisor.check_now() is False

    status = supervisor.status()

    assert status.healthy is False


@pytest.mark.asyncio
async def test_supervisor_records_failed_monitor_cycle() -> None:
    async def health_check() -> bool:
        return False

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    await supervisor.start()

    try:
        await asyncio.sleep(0.01)

        status = supervisor.status()

        assert status.running is True
        assert status.healthy is False
        assert status.restart_count >= 1
    finally:
        await supervisor.stop()


@pytest.mark.asyncio
async def test_supervisor_start_is_idempotent() -> None:
    async def health_check() -> bool:
        return True

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    await supervisor.start()
    first_task = supervisor._task

    try:
        await supervisor.start()
        assert supervisor._task is first_task
    finally:
        await supervisor.stop()


@pytest.mark.asyncio
async def test_supervisor_stop_is_safe() -> None:
    async def health_check() -> bool:
        return True

    supervisor = RuntimeSupervisor(
        health_check,
        interval_seconds=60,
    )

    await supervisor.stop()

    assert supervisor.status().running is False


def test_supervisor_rejects_invalid_interval() -> None:
    async def health_check() -> bool:
        return True

    with pytest.raises(
        ValueError,
        match="greater than 0",
    ):
        RuntimeSupervisor(
            health_check,
            interval_seconds=0,
        )
