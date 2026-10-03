from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentStatus


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' is already registered")
        self._agents[agent.name] = agent

    def get(self, name: str) -> AgentDefinition:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise KeyError(f"Agent '{name}' is not registered") from exc

    def list_agents(self) -> list[AgentDefinition]:
        return list(self._agents.values())

    def enable(self, name: str) -> None:
        agent = self.get(name)
        agent.status = AgentStatus.AVAILABLE

    def disable(self, name: str) -> None:
        agent = self.get(name)
        agent.status = AgentStatus.DISABLED
