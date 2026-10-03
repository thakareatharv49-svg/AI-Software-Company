from __future__ import annotations

from collections.abc import Iterable

from src.tasks.models.contracts import (
    Task,
    TaskCreateRequest,
    TaskUpdateRequest,
)
from src.tasks.models.enums import TaskPriority, TaskStatus
from src.tasks.repository.memory import InMemoryTaskRepository
from src.tasks.repository.protocol import TaskRepository


class TaskEngine:
    def __init__(self, repository: TaskRepository | None = None) -> None:
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
            return self.transition(task.id, TaskStatus.READY)

        return self.transition(task.id, TaskStatus.BLOCKED)

    def get(self, task_id: str) -> Task:
        return self.repository.get(task_id)

    def list(
        self,
        *,
        project_id: str | None = None,
        statuses: Iterable[TaskStatus] | None = None,
    ) -> list[Task]:
        return self.repository.list(
            project_id=project_id,
            statuses=statuses,
        )

    def update(self, task_id: str, request: TaskUpdateRequest) -> Task:
        task = self.get(task_id)

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
        return self.repository.save(task)

    def assign(self, task_id: str, agent_name: str) -> Task:
        task = self.get(task_id)
        task.assigned_agent = agent_name
        task.touch()
        return self.repository.save(task)

    def transition(self, task_id: str, status: TaskStatus) -> Task:
        task = self.get(task_id)

        allowed_transitions = {
            TaskStatus.PENDING: {
                TaskStatus.READY,
                TaskStatus.BLOCKED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.READY: {
                TaskStatus.IN_PROGRESS,
                TaskStatus.CANCELLED,
            },
            TaskStatus.BLOCKED: {
                TaskStatus.READY,
                TaskStatus.CANCELLED,
            },
            TaskStatus.IN_PROGRESS: {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.FAILED: {
                TaskStatus.READY,
                TaskStatus.CANCELLED,
            },
            TaskStatus.COMPLETED: set(),
            TaskStatus.CANCELLED: set(),
        }

        if status not in allowed_transitions[task.status]:
            raise ValueError(
                f"Invalid task transition: "
                f"{task.status.value} -> {status.value}"
            )

        task.status = status

        if status == TaskStatus.IN_PROGRESS:
            task.started_at = task.started_at or task.updated_at

        if status == TaskStatus.COMPLETED:
            task.completed_at = task.updated_at

        task.touch()
        return self.repository.save(task)

    def dependencies_completed(self, task: Task) -> bool:
        if not task.dependencies:
            return True

        dependencies = [
            self.repository.get(dependency_id)
            for dependency_id in task.dependencies
        ]

        return all(
            dependency.status == TaskStatus.COMPLETED
            for dependency in dependencies
        )

    def refresh_blocked_tasks(self) -> list[Task]:
        refreshed: list[Task] = []

        for task in self.repository.list(statuses=[TaskStatus.BLOCKED]):
            if self.dependencies_completed(task):
                refreshed.append(
                    self.transition(task.id, TaskStatus.READY)
                )

        return refreshed

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
            key=lambda task: (
                priority_order[task.priority],
                task.created_at,
            ),
        )

    def start(self, task_id: str) -> Task:
        return self.transition(task_id, TaskStatus.IN_PROGRESS)

    def complete(self, task_id: str) -> Task:
        return self.transition(task_id, TaskStatus.COMPLETED)

    def fail(self, task_id: str, error: str) -> Task:
        task = self.get(task_id)
        task.error = error
        return self.transition(task_id, TaskStatus.FAILED)

    def retry(self, task_id: str) -> Task:
        task = self.get(task_id)
        task.retry_count += 1
        task.error = None
        return self.transition(task_id, TaskStatus.READY)

    def cancel(self, task_id: str) -> Task:
        return self.transition(task_id, TaskStatus.CANCELLED)
