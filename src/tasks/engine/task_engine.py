from __future__ import annotations

from collections.abc import Iterable

from src.tasks.models.contracts import Task, TaskCreateRequest, TaskUpdateRequest
from src.tasks.models.enums import TaskPriority, TaskStatus
from src.tasks.repository.memory import InMemoryTaskRepository


class TaskEngine:
    _allowed_transitions: dict[TaskStatus, set[TaskStatus]] = {
        TaskStatus.PENDING: {
            TaskStatus.READY,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
        },
        TaskStatus.READY: {
            TaskStatus.IN_PROGRESS,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
        },
        TaskStatus.IN_PROGRESS: {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
        },
        TaskStatus.BLOCKED: {
            TaskStatus.READY,
            TaskStatus.CANCELLED,
        },
        TaskStatus.FAILED: {
            TaskStatus.READY,
            TaskStatus.CANCELLED,
        },
        TaskStatus.COMPLETED: set(),
        TaskStatus.CANCELLED: set(),
    }

    def __init__(self, repository: InMemoryTaskRepository | None = None) -> None:
        self.repository = repository or InMemoryTaskRepository()

    def create(self, request: TaskCreateRequest) -> Task:
        if not request.title.strip():
            raise ValueError("Task title cannot be empty")

        for dependency_id in request.dependencies:
            self.repository.get(dependency_id)

        task = Task(
            title=request.title.strip(),
            description=request.description,
            project_id=request.project_id,
            parent_task_id=request.parent_task_id,
            priority=request.priority,
            dependencies=list(request.dependencies),
        )

        self.repository.create(task)

        if self.dependencies_completed(task):
            self.transition(task.id, TaskStatus.READY)
        else:
            self.transition(task.id, TaskStatus.BLOCKED)

        return task

    def get(self, task_id: str) -> Task:
        return self.repository.get(task_id)

    def list(
        self,
        *,
        project_id: str | None = None,
        statuses: Iterable[TaskStatus] | None = None,
    ) -> list[Task]:
        return self.repository.list(project_id=project_id, statuses=statuses)

    def update(self, task_id: str, request: TaskUpdateRequest) -> Task:
        task = self.get(task_id)

        if task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.CANCELLED,
        }:
            raise ValueError(f"Cannot update terminal task: {task.id}")

        if request.title is not None:
            if not request.title.strip():
                raise ValueError("Task title cannot be empty")
            task.title = request.title.strip()

        if request.description is not None:
            task.description = request.description

        if request.priority is not None:
            task.priority = request.priority

        if request.assigned_agent is not None:
            task.assigned_agent = request.assigned_agent

        task.touch()
        return task

    def assign(self, task_id: str, agent_name: str) -> Task:
        if not agent_name.strip():
            raise ValueError("Agent name cannot be empty")

        task = self.get(task_id)

        if task.status not in {
            TaskStatus.READY,
            TaskStatus.PENDING,
            TaskStatus.BLOCKED,
        }:
            raise ValueError(f"Task cannot be assigned from {task.status}")

        task.assigned_agent = agent_name.strip()
        task.touch()
        return task

    def transition(self, task_id: str, new_status: TaskStatus) -> Task:
        task = self.get(task_id)

        if new_status == task.status:
            return task

        allowed = self._allowed_transitions[task.status]

        if new_status not in allowed:
            raise ValueError(
                f"Invalid task transition: {task.status} -> {new_status}"
            )

        task.status = new_status
        task.touch()

        if new_status == TaskStatus.IN_PROGRESS:
            task.started_at = task.started_at or task.updated_at

        if new_status == TaskStatus.COMPLETED:
            task.completed_at = task.updated_at
            task.error = None

        return task

    def dependencies_completed(self, task: Task) -> bool:
        return all(
            self.get(dependency_id).status == TaskStatus.COMPLETED
            for dependency_id in task.dependencies
        )

    def refresh_blocked_tasks(self) -> list[Task]:
        changed: list[Task] = []

        for task in self.repository.list(statuses=[TaskStatus.BLOCKED]):
            if self.dependencies_completed(task):
                self.transition(task.id, TaskStatus.READY)
                changed.append(task)

        return changed

    def ready_tasks(self, project_id: str | None = None) -> list[Task]:
        self.refresh_blocked_tasks()

        tasks = self.repository.list(
            project_id=project_id,
            statuses=[TaskStatus.READY],
        )

        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }

        return sorted(
            tasks,
            key=lambda task: (priority_order[task.priority], task.created_at),
        )

    def start(self, task_id: str) -> Task:
        return self.transition(task_id, TaskStatus.IN_PROGRESS)

    def complete(self, task_id: str) -> Task:
        task = self.transition(task_id, TaskStatus.COMPLETED)
        self.refresh_blocked_tasks()
        return task

    def fail(self, task_id: str, error: str) -> Task:
        task = self.transition(task_id, TaskStatus.FAILED)
        task.error = error
        task.touch()
        return task

    def retry(self, task_id: str) -> Task:
        task = self.get(task_id)

        if task.status != TaskStatus.FAILED:
            raise ValueError("Only failed tasks can be retried")

        task.retry_count += 1
        task.error = None
        task.touch()
        self.transition(task.id, TaskStatus.READY)
        return task

    def cancel(self, task_id: str) -> Task:
        return self.transition(task_id, TaskStatus.CANCELLED)
