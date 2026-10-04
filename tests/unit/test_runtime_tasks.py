import asyncio

import pytest

from src.company.runtime import (
    RuntimeTaskExecutor,
    RuntimeTaskRegistry,
)


@pytest.mark.asyncio
async def test_task_registration() -> None:
    registry = RuntimeTaskRegistry()

    task = await registry.register("task-1")

    assert task.task_id == "task-1"
    assert task.state == "pending"


@pytest.mark.asyncio
async def test_duplicate_task_is_rejected() -> None:
    registry = RuntimeTaskRegistry()

    await registry.register("task-1")

    with pytest.raises(ValueError, match="already registered"):
        await registry.register("task-1")


@pytest.mark.asyncio
async def test_task_executor_completes_successfully() -> None:
    registry = RuntimeTaskRegistry()
    executor = RuntimeTaskExecutor(registry)

    async def operation() -> str:
        return "success"

    result = await executor.execute("task-1", operation)

    assert result == "success"

    task = await registry.get("task-1")
    assert task is not None
    assert task.state == "completed"


@pytest.mark.asyncio
async def test_task_executor_records_failure() -> None:
    registry = RuntimeTaskRegistry()
    executor = RuntimeTaskExecutor(registry)

    async def operation() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await executor.execute("task-1", operation)

    task = await registry.get("task-1")
    assert task is not None
    assert task.state == "failed"


@pytest.mark.asyncio
async def test_task_executor_records_cancellation() -> None:
    registry = RuntimeTaskRegistry()
    executor = RuntimeTaskExecutor(registry)

    started = asyncio.Event()
    release = asyncio.Event()

    async def operation() -> None:
        started.set()
        await release.wait()

    task = asyncio.create_task(
        executor.execute("task-1", operation)
    )

    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    recorded = await registry.get("task-1")
    assert recorded is not None
    assert recorded.state == "cancelled"


@pytest.mark.asyncio
async def test_registry_lists_tasks() -> None:
    registry = RuntimeTaskRegistry()

    await registry.register("task-1")
    await registry.register("task-2")

    tasks = await registry.list()

    assert len(tasks) == 2
    assert {task.task_id for task in tasks} == {"task-1", "task-2"}


@pytest.mark.asyncio
async def test_registry_removes_task() -> None:
    registry = RuntimeTaskRegistry()

    await registry.register("task-1")
    await registry.remove("task-1")

    assert await registry.get("task-1") is None


@pytest.mark.asyncio
async def test_unknown_task_update_is_rejected() -> None:
    registry = RuntimeTaskRegistry()

    with pytest.raises(KeyError):
        await registry.update("missing", "running")
