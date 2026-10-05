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
    status: str = "planned"


class MissionPlan(BaseModel):
    mission_id: str
    name: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    steps: list[PlannedStep]
