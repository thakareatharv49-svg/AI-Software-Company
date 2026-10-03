from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class Mission:
    name: str
    objective: str
    project_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class TaskPlanItem:
    title: str
    description: str = ""
    priority: str = "medium"
    dependencies: tuple[int, ...] = ()


@dataclass(slots=True, frozen=True)
class ManagerDecision:
    decision: str
    reason: str
    task_id: str | None = None
    agent_name: str | None = None
