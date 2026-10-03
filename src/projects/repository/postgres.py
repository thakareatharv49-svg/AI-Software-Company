from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.project import ProjectModel
from src.projects.models.contracts import Project
from src.projects.models.enums import ProjectStatus


class PostgresProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_domain(model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            name=model.name,
            description=model.description,
            objective=model.objective,
            repository=model.repository,
            status=ProjectStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, project: Project) -> Project:
        model = self.session.get(ProjectModel, project.id)

        if model is None:
            model = ProjectModel(
                id=project.id,
                name=project.name,
                description=project.description,
                objective=project.objective,
                repository=project.repository,
                status=project.status.value,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            self.session.add(model)
        else:
            model.name = project.name
            model.description = project.description
            model.objective = project.objective
            model.repository = project.repository
            model.status = project.status.value
            model.updated_at = project.updated_at

        self.session.commit()
        return self._to_domain(model)

    def get(self, project_id: str) -> Project:
        model = self.session.get(ProjectModel, project_id)

        if model is None:
            raise KeyError(f"Project '{project_id}' is not registered")

        return self._to_domain(model)

    def list(self, status: ProjectStatus | None = None) -> list[Project]:
        statement = select(ProjectModel).order_by(ProjectModel.created_at)

        if status is not None:
            statement = statement.where(ProjectModel.status == status.value)

        models = self.session.scalars(statement).all()
        return [self._to_domain(model) for model in models]

    def delete(self, project_id: str) -> None:
        model = self.session.get(ProjectModel, project_id)

        if model is None:
            raise KeyError(f"Project '{project_id}' is not registered")

        self.session.delete(model)
        self.session.commit()
