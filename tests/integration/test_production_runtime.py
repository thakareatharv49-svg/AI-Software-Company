import asyncio

import pytest

from src.company.runtime import ProductionRuntime, RuntimeConfig


@pytest.mark.asyncio
async def test_production_runtime_starts_and_stops() -> None:
    config = RuntimeConfig(
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        max_concurrent_runs=2,
        shutdown_timeout_seconds=1,
    )

    runtime = ProductionRuntime(config)

    status = await runtime.status()
    assert status["running"] is False

    await runtime.start()

    status = await runtime.status()
    assert status["running"] is True
    assert status["active_runs"] == 0
    assert status["max_concurrent_runs"] == 2

    await runtime.stop()

    status = await runtime.status()
    assert status["running"] is False


@pytest.mark.asyncio
async def test_production_runtime_executes_operation() -> None:
    config = RuntimeConfig(
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        max_concurrent_runs=1,
        shutdown_timeout_seconds=1,
    )

    runtime = ProductionRuntime(config)
    await runtime.start()

    async def operation() -> str:
        await asyncio.sleep(0.01)
        return "success"

    result = await runtime.execute(operation)

    assert result.completed is True
    assert result.timed_out is False

    status = await runtime.status()

    assert status["metrics"].total_started == 1
    assert status["metrics"].total_completed == 1
    assert status["metrics"].total_failed == 0
    assert status["capacity"].active_tasks == 0

    await runtime.stop()


@pytest.mark.asyncio
async def test_production_runtime_records_failure() -> None:
    config = RuntimeConfig(
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        max_concurrent_runs=1,
        shutdown_timeout_seconds=1,
    )

    runtime = ProductionRuntime(config)
    await runtime.start()

    async def operation() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await runtime.execute(operation)

    status = await runtime.status()

    assert status["metrics"].total_started == 1
    assert status["metrics"].total_completed == 0
    assert status["metrics"].total_failed == 1
    assert len(status["alerts"]) >= 1
    assert status["capacity"].active_tasks == 0

    await runtime.stop()


@pytest.mark.asyncio
async def test_production_runtime_rejects_execution_before_start() -> None:
    runtime = ProductionRuntime(
        RuntimeConfig(
            environment="test",
            host="127.0.0.1",
            port=8000,
            debug=False,
            max_concurrent_runs=1,
            shutdown_timeout_seconds=1,
        )
    )

    async def operation() -> str:
        return "should not run"

    with pytest.raises(RuntimeError, match="not running"):
        await runtime.execute(operation)


@pytest.mark.asyncio
async def test_production_runtime_timeout_is_observable() -> None:
    runtime = ProductionRuntime(
        RuntimeConfig(
            environment="test",
            host="127.0.0.1",
            port=8000,
            debug=False,
            max_concurrent_runs=1,
            shutdown_timeout_seconds=0.01,
        )
    )

    await runtime.start()

    async def operation() -> None:
        await asyncio.sleep(0.1)

    with pytest.raises(TimeoutError, match="timed out"):
        await runtime.execute(operation)

    status = await runtime.status()

    assert status["metrics"].total_started == 1
    assert status["metrics"].total_failed == 1
    assert any(
        alert.metric == "timeouts"
        for alert in status["alerts"]
    )

    await runtime.stop()
