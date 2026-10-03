from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.projects.models.enums import ProjectStatus


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    objective: str = ""
    repository: str | None = None


class Project(BaseModel):
    id: str
    name: str
    description: str = ""
    objective: str = ""
    repository: str | None = None
    status: ProjectStatus = ProjectStatus.IDEA
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
