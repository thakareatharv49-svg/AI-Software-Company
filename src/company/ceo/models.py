from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class MissionStatus(StrEnum):
    RECEIVED = "received"
    PLANNED = "planned"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionType(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    DEFER = "defer"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class Mission:
    mission_id: str
    objective: str
    constraints: tuple[str, ...] = ()
    priority: str = "normal"
    status: MissionStatus = MissionStatus.RECEIVED
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MissionPlan:
    mission_id: str
    objective: str
    goals: tuple[str, ...]
    tasks: tuple[str, ...]
    risks: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    decision_type: DecisionType
    reason: str
    confidence: float = 1.0
    requires_human: bool = False


@dataclass(frozen=True)
class CEOResult:
    mission: Mission
    plan: MissionPlan
    decision: Decision
