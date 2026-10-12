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


class MissionPlan(BaseModel):
    mission_id: str
    name: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    # Requirements remain attached to the durable plan so QA and review can
    # trace a finished product back to the user's original request.
    acceptance_criteria: list[str] = Field(default_factory=list)
    steps: list[PlannedStep]
