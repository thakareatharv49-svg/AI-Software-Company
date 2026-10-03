from typing import Protocol

from src.projects.models.contracts import Project
from src.projects.models.enums import ProjectStatus


class ProjectRepository(Protocol):
    def save(self, project: Project) -> Project: ...

    def get(self, project_id: str) -> Project: ...

    def list(
        self,
        status: ProjectStatus | None = None,
    ) -> list[Project]: ...

    def delete(self, project_id: str) -> None: ...
