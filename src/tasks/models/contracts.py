from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.tasks.models.enums import TaskPriority, TaskStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Task:
    title: str
    description: str = ""
    project_id: str | None = None
    parent_task_id: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str | None = None
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    retry_count: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    def touch(self) -> None:
        self.updated_at = utc_now()


@dataclass(slots=True, frozen=True)
class TaskCreateRequest:
    title: str
    description: str = ""
    project_id: str | None = None
    parent_task_id: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class TaskUpdateRequest:
    title: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    assigned_agent: str | None = None
