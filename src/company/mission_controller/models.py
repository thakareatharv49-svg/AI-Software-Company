from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class MissionStage(StrEnum):
    RESEARCH = "research"
    PRODUCT = "product"
    ARCHITECTURE = "architecture"
    TASKS = "tasks"
    AGENTS = "agents"
    EXECUTION = "execution"
    QA = "qa"
    SECURITY = "security"
    GITHUB = "github"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    LEARNING = "learning"


class PlannedStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    stage: MissionStage
    objective: str
    # Explicit prerequisites let planning/QA reason about ordering rather than
    # inferring a dependency graph from the list position alone.
    depends_on: list[str] = Field(default_factory=list)
    agent_role: str = "generalist"
    status: str = "planned"
    attempts: int = 0
    detail: str | None = None


class EngineeringTask(BaseModel):
    """A small, traceable unit of product work within a mission."""

    id: str
    title: str
    requirement: str
    workstream: str
    depends_on: list[str] = Field(default_factory=list)
    agent_role: str
    acceptance_check: str
    status: str = "planned"


class MissionPlan(BaseModel):
    mission_id: str
    name: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    # Requirements remain attached to the durable plan so QA and review can
    # trace a finished product back to the user's original request.
    acceptance_criteria: list[str] = Field(default_factory=list)
    # Feature-level work items make large missions actionable without replacing
    # the existing lifecycle stages that coordinate the company.
    engineering_tasks: list[EngineeringTask] = Field(default_factory=list)
    # Server-generated provenance from the actual QA runner and security reviewer.
    qa_status: str | None = None
    qa_exit_code: int | None = None
    qa_duration_ms: int | None = None
    qa_command: list[str] = Field(default_factory=list)
    qa_evidence: str | None = None
    security_status: str | None = None
    security_summary: str | None = None
    security_evidence: str | None = None
    steps: list[PlannedStep]

