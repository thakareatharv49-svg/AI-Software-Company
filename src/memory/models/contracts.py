from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from src.memory.models.enums import MemoryType


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    memory_type: MemoryType
    title: str
    content: str
    project_id: str | None = None
    agent_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class MemoryCreateRequest(BaseModel):
    memory_type: MemoryType
    title: str
    content: str
    project_id: str | None = None
    agent_name: str | None = None
    tags: list[str] = Field(default_factory=list)


class MemorySearchRequest(BaseModel):
    query: str
    memory_type: MemoryType | None = None
    project_id: str | None = None
    limit: int = Field(default=10, ge=1, le=100)
