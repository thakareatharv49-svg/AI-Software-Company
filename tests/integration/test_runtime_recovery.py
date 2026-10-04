import pytest

from src.company.runtime import (
    ProductionRuntime,
    RecoveringProductionRuntime,
    RuntimeConfig,
    RuntimeRecoveryController,
)


def make_runtime() -> ProductionRuntime:
    return ProductionRuntime(
        RuntimeConfig(
            environment="test",
            host="127.0.0.1",
            port=8000,
            debug=False,
            max_concurrent_runs=1,
            shutdown_timeout_seconds=1,
        )
    )


@pytest.mark.asyncio
async def test_recovery_controller_tracks_attempts() -> None:
    controller = RuntimeRecoveryController(max_attempts=3)

    first = await controller.begin_attempt()
    second = await controller.begin_attempt()

    assert first.attempts == 1
    assert first.exhausted is False
    assert second.attempts == 2
    assert second.exhausted is False


@pytest.mark.asyncio
async def test_recovery_controller_exhausts_attempts() -> None:
    controller = RuntimeRecoveryController(max_attempts=2)

    await controller.begin_attempt()
    state = await controller.begin_attempt()

    assert state.attempts == 2
    assert state.exhausted is True


@pytest.mark.asyncio
async def test_recovery_controller_marks_recovered() -> None:
    controller = RuntimeRecoveryController(max_attempts=3)

    await controller.begin_attempt()
    state = await controller.mark_recovered()

    assert state.recovered is True
    assert state.attempts == 1
    assert state.exhausted is False


@pytest.mark.asyncio
async def test_recovery_controller_reset() -> None:
    controller = RuntimeRecoveryController(max_attempts=2)

    await controller.begin_attempt()
    await controller.reset()

    state = await controller.state()

    assert state.attempts == 0
    assert state.recovered is False
    assert state.exhausted is False


@pytest.mark.asyncio
async def test_recovering_runtime_retries_failed_operation() -> None:
    runtime = make_runtime()
    recovery = RuntimeRecoveryController(max_attempts=3)
    recovering = RecoveringProductionRuntime(runtime, recovery)

    await runtime.start()

    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise RuntimeError("temporary failure")

        return "success"

    result = await recovering.execute(operation)

    assert result.completed is True
    assert attempts == 3

    state = await recovery.state()

    assert state.attempts == 3
    assert state.recovered is True

    await runtime.stop()


@pytest.mark.asyncio
async def test_recovering_runtime_stops_after_max_attempts() -> None:
    runtime = make_runtime()
    recovery = RuntimeRecoveryController(max_attempts=2)
    recovering = RecoveringProductionRuntime(runtime, recovery)

    await runtime.start()

    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        await recovering.execute(operation)

    assert attempts == 2

    state = await recovery.state()

    assert state.attempts == 2
    assert state.exhausted is True

    await runtime.stop()


def test_invalid_recovery_limit_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RuntimeRecoveryController(max_attempts=0)
