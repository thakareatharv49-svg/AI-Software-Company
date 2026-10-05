from __future__ import annotations

from dataclasses import dataclass

from company.tools.models import ToolDefinition, ToolPermissionError, ToolRequest, ToolRisk


@dataclass(frozen=True)
class ToolPermissionPolicy:
    allowed_risks: frozenset[ToolRisk] = frozenset({ToolRisk.READ})
    allowed_tools: frozenset[str] = frozenset()
    deny_tools: frozenset[str] = frozenset()

    def allows(self, definition: ToolDefinition, request: ToolRequest) -> bool:
        if definition.name in self.deny_tools:
            return False

        if definition.name in self.allowed_tools:
            return True

        if self.allowed_tools and definition.name not in self.allowed_tools:
            return False

        return definition.risk in self.allowed_risks


class ToolPermissionEngine:
    def __init__(
        self,
        policy: ToolPermissionPolicy | None = None,
    ) -> None:
        self.policy = policy or ToolPermissionPolicy()

    def authorize(
        self,
        definition: ToolDefinition,
        request: ToolRequest,
    ) -> None:
        if not self.policy.allows(definition, request):
            raise ToolPermissionError(
                f"Tool execution denied: {definition.name}"
            )
