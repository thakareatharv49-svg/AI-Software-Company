from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    MISSION = "mission"
    PROJECT = "project"
    DECISION = "decision"
    TASK = "task"
    FAILURE = "failure"
    LESSON = "lesson"
    AGENT = "agent"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"


@dataclass
class MemoryEntry:
    memory_id: str
    memory_type: MemoryType
    title: str
    content: str
    project_id: str | None = None
    run_id: str | None = None
    agent_id: str | None = None
    importance: int = 5
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
