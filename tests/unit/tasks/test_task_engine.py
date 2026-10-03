import pytest

from src.tasks.engine.task_engine import TaskEngine
from src.tasks.models.contracts import TaskCreateRequest
from src.tasks.models.enums import TaskPriority, TaskStatus


def test_create_task_becomes_ready_without_dependencies() -> None:
    engine = TaskEngine()

    task = engine.create(
        TaskCreateRequest(
            title="Build API",
            priority=TaskPriority.HIGH,
        )
    )

    assert task.status == TaskStatus.READY
    assert task.priority == TaskPriority.HIGH


def test_dependencies_block_task_until_completed() -> None:
    engine = TaskEngine()

    first = engine.create(TaskCreateRequest(title="Research"))
    second = engine.create(
        TaskCreateRequest(
            title="Implement",
            dependencies=(first.id,),
        )
    )

    assert second.status == TaskStatus.BLOCKED

    engine.start(first.id)
    engine.complete(first.id)

    ready = engine.ready_tasks()

    assert second.id in {task.id for task in ready}


def test_invalid_transition_is_rejected() -> None:
    engine = TaskEngine()
    task = engine.create(TaskCreateRequest(title="Test"))

    with pytest.raises(ValueError, match="Invalid task transition"):
        engine.transition(task.id, TaskStatus.COMPLETED)


def test_failed_task_can_be_retried() -> None:
    engine = TaskEngine()
    task = engine.create(TaskCreateRequest(title="Build"))

    engine.start(task.id)
    engine.fail(task.id, "Compilation failed")

    assert task.status == TaskStatus.FAILED
    assert task.error == "Compilation failed"

    engine.retry(task.id)

    assert task.status == TaskStatus.READY
    assert task.retry_count == 1
    assert task.error is None


def test_priority_orders_ready_tasks() -> None:
    engine = TaskEngine()

    low = engine.create(
        TaskCreateRequest(title="Low", priority=TaskPriority.LOW)
    )
    critical = engine.create(
        TaskCreateRequest(title="Critical", priority=TaskPriority.CRITICAL)
    )

    ready = engine.ready_tasks()

    assert ready[0].id == critical.id
    assert ready[1].id == low.id
