from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class CompanyEvent(BaseModel):
    event_type: str
    project_id: str | None = None
    task_id: str | None = None
    agent_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
