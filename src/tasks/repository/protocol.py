from collections.abc import Iterable
from typing import Protocol

from src.tasks.models.contracts import Task
from src.tasks.models.enums import TaskStatus


class TaskRepository(Protocol):
    def create(self, task: Task) -> Task: ...

    def get(self, task_id: str) -> Task: ...

    def list(
        self,
        *,
        project_id: str | None = None,
        statuses: Iterable[TaskStatus] | None = None,
    ) -> list[Task]: ...

    def save(self, task: Task) -> Task: ...

    def delete(self, task_id: str) -> None: ...
