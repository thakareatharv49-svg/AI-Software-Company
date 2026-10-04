import asyncio

import pytest

from src.company.runtime import RuntimeHeartbeatMonitor


@pytest.mark.asyncio
async def test_heartbeat_check_records_health() -> None:
    async def health_check() -> bool:
        return True

    monitor = RuntimeHeartbeatMonitor(
        health_check,
        interval_seconds=60,
    )

    heartbeat = await monitor.check()

    assert heartbeat.healthy is True
    assert heartbeat.timestamp > 0
    assert monitor.last_heartbeat == heartbeat


@pytest.mark.asyncio
async def test_unhealthy_heartbeat_is_recorded() -> None:
    async def health_check() -> bool:
        return False

    monitor = RuntimeHeartbeatMonitor(
        health_check,
        interval_seconds=60,
    )

    heartbeat = await monitor.check()

    assert heartbeat.healthy is False


@pytest.mark.asyncio
async def test_heartbeat_monitor_starts() -> None:
    checks = 0
    first_check = asyncio.Event()

    async def health_check() -> bool:
        nonlocal checks
        checks += 1
        first_check.set()
        return True

    monitor = RuntimeHeartbeatMonitor(
        health_check,
        interval_seconds=60,
    )

    await monitor.start()

    try:
        await asyncio.wait_for(first_check.wait(), timeout=1)
        assert monitor.running is True
        assert checks >= 1
    finally:
        await monitor.stop()


@pytest.mark.asyncio
async def test_heartbeat_monitor_stops() -> None:
    async def health_check() -> bool:
        return True

    monitor = RuntimeHeartbeatMonitor(
        health_check,
        interval_seconds=60,
    )

    await monitor.start()
    assert monitor.running is True

    await monitor.stop()

    assert monitor.running is False


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    checks = 0

    async def health_check() -> bool:
        nonlocal checks
        checks += 1
        return True

    monitor = RuntimeHeartbeatMonitor(
        health_check,
        interval_seconds=60,
    )

    await monitor.start()
    first_task = monitor._task

    try:
        await monitor.start()
        assert monitor._task is first_task
    finally:
        await monitor.stop()


@pytest.mark.asyncio
async def test_stop_without_start_is_safe() -> None:
    async def health_check() -> bool:
        return True

    monitor = RuntimeHeartbeatMonitor(
        health_check,
        interval_seconds=60,
    )

    await monitor.stop()

    assert monitor.running is False


def test_invalid_interval_is_rejected() -> None:
    async def health_check() -> bool:
        return True

    with pytest.raises(
        ValueError,
        match="greater than 0",
    ):
        RuntimeHeartbeatMonitor(
            health_check,
            interval_seconds=0,
        )
