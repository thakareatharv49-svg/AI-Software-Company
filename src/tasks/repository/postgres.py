from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.task import TaskModel
from src.tasks.models.contracts import Task
from src.tasks.models.enums import TaskPriority, TaskStatus


class PostgresTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_domain(model: TaskModel) -> Task:
        return Task(
            id=model.id,
            title=model.title,
            description=model.description,
            project_id=model.project_id,
            parent_task_id=model.parent_task_id,
            priority=TaskPriority(model.priority),
            status=TaskStatus(model.status),
            assigned_agent=model.assigned_agent,
            dependencies=list(model.dependencies),
            metadata=dict(model.task_metadata),
            retry_count=model.retry_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error=model.error,
        )

    def create(self, task: Task) -> Task:
        if self.session.get(TaskModel, task.id) is not None:
            raise ValueError(f"Task already exists: {task.id}")

        model = TaskModel(
            id=task.id,
            title=task.title,
            description=task.description,
            project_id=task.project_id,
            parent_task_id=task.parent_task_id,
            priority=task.priority.value,
            status=task.status.value,
            assigned_agent=task.assigned_agent,
            dependencies=list(task.dependencies),
            task_metadata=dict(task.metadata),
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error=task.error,
        )

        self.session.add(model)
        self.session.commit()
        return self._to_domain(model)

    def get(self, task_id: str) -> Task:
        model = self.session.get(TaskModel, task_id)

        if model is None:
            raise KeyError(f"Task not found: {task_id}")

        return self._to_domain(model)

    def list(
        self,
        *,
        project_id: str | None = None,
        statuses: Iterable[TaskStatus] | None = None,
    ) -> list[Task]:
        statement = select(TaskModel).order_by(TaskModel.created_at)

        if project_id is not None:
            statement = statement.where(TaskModel.project_id == project_id)

        if statuses is not None:
            values = [status.value for status in statuses]
            statement = statement.where(TaskModel.status.in_(values))

        models = self.session.scalars(statement).all()
        return [self._to_domain(model) for model in models]

    def save(self, task: Task) -> Task:
        model = self.session.get(TaskModel, task.id)

        if model is None:
            raise KeyError(f"Task not found: {task.id}")

        model.title = task.title
        model.description = task.description
        model.project_id = task.project_id
        model.parent_task_id = task.parent_task_id
        model.priority = task.priority.value
        model.status = task.status.value
        model.assigned_agent = task.assigned_agent
        model.dependencies = list(task.dependencies)
        model.task_metadata = dict(task.metadata)
        model.retry_count = task.retry_count
        model.updated_at = task.updated_at
        model.started_at = task.started_at
        model.completed_at = task.completed_at
        model.error = task.error

        self.session.commit()
        return self._to_domain(model)

    def delete(self, task_id: str) -> None:
        model = self.session.get(TaskModel, task_id)

        if model is None:
            raise KeyError(f"Task not found: {task_id}")

        self.session.delete(model)
        self.session.commit()
