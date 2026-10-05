from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ProjectOutputManifest(BaseModel):
    id: str
    mission_id: str
    project_id: str
    name: str
    status: str
    output_type: str = "factory_project"
    repository: str | None = None
    github_message: str | None = None
    memory_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
