from collections.abc import Iterable

from src.tasks.models.contracts import Task
from src.tasks.models.enums import TaskStatus


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create(self, task: Task) -> Task:
        if task.id in self._tasks:
            raise ValueError(f"Task already exists: {task.id}")

        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise KeyError(f"Task not found: {task_id}") from exc

    def list(
        self,
        *,
        project_id: str | None = None,
        statuses: Iterable[TaskStatus] | None = None,
    ) -> list[Task]:
        status_set = set(statuses) if statuses is not None else None

        tasks = list(self._tasks.values())

        if project_id is not None:
            tasks = [task for task in tasks if task.project_id == project_id]

        if status_set is not None:
            tasks = [task for task in tasks if task.status in status_set]

        return tasks

    def delete(self, task_id: str) -> None:
        self.get(task_id)
        del self._tasks[task_id]
