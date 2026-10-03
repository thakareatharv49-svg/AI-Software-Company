from pydantic import BaseModel, Field

from src.agents.models.enums import AgentPermission, AgentStatus


class AgentDefinition(BaseModel):
    name: str
    role: str
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    permissions: set[AgentPermission] = Field(default_factory=set)
    status: AgentStatus = AgentStatus.AVAILABLE
    max_concurrent_tasks: int = Field(default=1, ge=1)


class AgentRequest(BaseModel):
    task_id: str
    instruction: str
    context: dict[str, object] = Field(default_factory=dict)


class AgentResult(BaseModel):
    task_id: str
    agent_name: str
    success: bool
    output: str = ""
    error: str | None = None
    duration_ms: int | None = None
