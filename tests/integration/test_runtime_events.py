import asyncio

import pytest

from src.company.runtime import (
    ObservableProductionRuntime,
    ProductionRuntime,
    RuntimeConfig,
    RuntimeEventRecorder,
)


def make_runtime(timeout: float = 1.0) -> ProductionRuntime:
    return ProductionRuntime(
        RuntimeConfig(
            environment="test",
            host="127.0.0.1",
            port=8000,
            debug=False,
            max_concurrent_runs=2,
            shutdown_timeout_seconds=timeout,
        )
    )


@pytest.mark.asyncio
async def test_runtime_events_record_lifecycle() -> None:
    recorder = RuntimeEventRecorder()
    runtime = ObservableProductionRuntime(make_runtime(), recorder)

    await runtime.start()
    await runtime.stop()

    events = await recorder.list_events()

    assert [event.event_type for event in events] == [
        "runtime.started",
        "runtime.stopped",
    ]


@pytest.mark.asyncio
async def test_runtime_events_record_successful_execution() -> None:
    recorder = RuntimeEventRecorder()
    runtime = ObservableProductionRuntime(make_runtime(), recorder)

    await runtime.start()

    async def operation() -> str:
        await asyncio.sleep(0.01)
        return "success"

    result = await runtime.execute(operation)

    assert result.completed is True

    events = await recorder.list_events()

    assert [event.event_type for event in events] == [
        "runtime.started",
        "runtime.execution.started",
        "runtime.execution.completed",
    ]

    await runtime.stop()


@pytest.mark.asyncio
async def test_runtime_events_record_failed_execution() -> None:
    recorder = RuntimeEventRecorder()
    runtime = ObservableProductionRuntime(make_runtime(), recorder)

    await runtime.start()

    async def operation() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await runtime.execute(operation)

    failed = await recorder.events_by_type("runtime.execution.failed")

    assert len(failed) == 1
    assert failed[0].payload["error_type"] == "RuntimeError"
    assert failed[0].payload["error"] == "boom"

    await runtime.stop()


@pytest.mark.asyncio
async def test_event_recorder_clear() -> None:
    recorder = RuntimeEventRecorder()

    await recorder.record("test.event", {"value": 1})
    assert len(await recorder.list_events()) == 1

    await recorder.clear()

    assert await recorder.list_events() == []


@pytest.mark.asyncio
async def test_event_payload_is_copied() -> None:
    recorder = RuntimeEventRecorder()
    payload = {"value": 1}

    event = await recorder.record("test.event", payload)
    payload["value"] = 2

    assert event.payload["value"] == 1
