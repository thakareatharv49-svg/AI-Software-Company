from src.projects.models.contracts import Project
from src.projects.models.enums import ProjectStatus


class ProjectRepository:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

    def save(self, project: Project) -> Project:
        self._projects[project.id] = project
        return project

    def get(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Project '{project_id}' is not registered") from exc

    def list(
        self,
        status: ProjectStatus | None = None,
    ) -> list[Project]:
        projects = list(self._projects.values())

        if status is not None:
            projects = [
                project for project in projects if project.status == status
            ]

        return projects

    def delete(self, project_id: str) -> None:
        if project_id not in self._projects:
            raise KeyError(f"Project '{project_id}' is not registered")

        del self._projects[project_id]
