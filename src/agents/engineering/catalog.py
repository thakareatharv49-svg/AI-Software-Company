from pydantic import BaseModel, Field

from src.agents.engineering.enums import EngineeringRole


class EngineeringAgentSpec(BaseModel):
    name: str
    role: EngineeringRole
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    priority: int = Field(default=100, ge=1)


class EngineeringAgentCatalog:
    def __init__(self) -> None:
        self._agents: dict[str, EngineeringAgentSpec] = {}

    def register(self, agent: EngineeringAgentSpec) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Engineering agent '{agent.name}' already exists")

        self._agents[agent.name] = agent

    def get(self, name: str) -> EngineeringAgentSpec:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(
                f"Engineering agent '{name}' is not registered"
            ) from exc

    def list_agents(self) -> list[EngineeringAgentSpec]:
        return sorted(
            self._agents.values(),
            key=lambda agent: (agent.priority, agent.name),
        )

    def by_role(
        self,
        role: EngineeringRole,
    ) -> list[EngineeringAgentSpec]:
        return [
            agent
            for agent in self.list_agents()
            if agent.role == role
        ]
