from datetime import UTC, datetime
from uuid import uuid4

from src.projects.models.contracts import Project, ProjectCreateRequest
from src.projects.models.enums import ProjectStatus
from src.projects.repository.repository import ProjectRepository


class ProjectEngine:
    _TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
        ProjectStatus.IDEA: {
            ProjectStatus.RESEARCH,
            ProjectStatus.CANCELLED,
            ProjectStatus.ABANDONED,
        },
        ProjectStatus.RESEARCH: {
            ProjectStatus.VALIDATION,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.VALIDATION: {
            ProjectStatus.PLANNING,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.PLANNING: {
            ProjectStatus.ARCHITECTURE,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.ARCHITECTURE: {
            ProjectStatus.DEVELOPMENT,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.DEVELOPMENT: {
            ProjectStatus.TESTING,
            ProjectStatus.DEBUGGING,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.TESTING: {
            ProjectStatus.DEBUGGING,
            ProjectStatus.SECURITY,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.DEBUGGING: {
            ProjectStatus.TESTING,
            ProjectStatus.SECURITY,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.SECURITY: {
            ProjectStatus.REVIEW,
            ProjectStatus.DEBUGGING,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.REVIEW: {
            ProjectStatus.RELEASE,
            ProjectStatus.DEBUGGING,
            ProjectStatus.BLOCKED,
            ProjectStatus.CANCELLED,
        },
        ProjectStatus.RELEASE: {
            ProjectStatus.MONITORING,
            ProjectStatus.COMPLETED,
            ProjectStatus.BLOCKED,
        },
        ProjectStatus.MONITORING: {
            ProjectStatus.COMPLETED,
            ProjectStatus.BLOCKED,
        },
        ProjectStatus.BLOCKED: {
            ProjectStatus.RESEARCH,
            ProjectStatus.PLANNING,
            ProjectStatus.DEVELOPMENT,
            ProjectStatus.TESTING,
            ProjectStatus.DEBUGGING,
            ProjectStatus.SECURITY,
            ProjectStatus.REVIEW,
            ProjectStatus.CANCELLED,
            ProjectStatus.ABANDONED,
        },
        ProjectStatus.COMPLETED: set(),
        ProjectStatus.CANCELLED: set(),
        ProjectStatus.ABANDONED: set(),
    }

    def __init__(self, repository: ProjectRepository | None = None) -> None:
        self.repository = repository or ProjectRepository()

    def create(self, request: ProjectCreateRequest) -> Project:
        if not request.name.strip():
            raise ValueError("Project name cannot be empty")

        if not request.objective.strip():
            raise ValueError("Project objective cannot be empty")

        now = datetime.now(UTC)

        project = Project(
            id=str(uuid4()),
            name=request.name.strip(),
            description=request.description.strip(),
            objective=request.objective.strip(),
            repository=request.repository,
            status=ProjectStatus.IDEA,
            created_at=now,
            updated_at=now,
        )

        return self.repository.save(project)

    def get(self, project_id: str) -> Project:
        return self.repository.get(project_id)

    def list(self, status: ProjectStatus | None = None) -> list[Project]:
        return self.repository.list(status)

    def transition(
        self,
        project_id: str,
        status: ProjectStatus,
    ) -> Project:
        project = self.repository.get(project_id)

        if status == project.status:
            return project

        allowed = self._TRANSITIONS.get(project.status, set())

        if status not in allowed:
            raise ValueError(
                f"Invalid project transition: "
                f"{project.status.value} -> {status.value}"
            )

        project.status = status
        project.updated_at = datetime.now(UTC)

        return self.repository.save(project)

    def complete(self, project_id: str) -> Project:
        return self.transition(project_id, ProjectStatus.COMPLETED)

    def block(self, project_id: str) -> Project:
        return self.transition(project_id, ProjectStatus.BLOCKED)
