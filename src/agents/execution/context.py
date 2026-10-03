from dataclasses import dataclass, field

from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission


@dataclass(frozen=True)
class AgentExecutionContext:
    agent: AgentDefinition
    allowed_permissions: frozenset[AgentPermission] = field(default_factory=frozenset)

    def can(self, permission: AgentPermission) -> bool:
        return permission in self.allowed_permissions and permission in self.agent.permissions

    def require(self, permission: AgentPermission) -> None:
        if not self.can(permission):
            raise PermissionError(
                f"Agent '{self.agent.name}' does not have permission '{permission.value}'"
            )
