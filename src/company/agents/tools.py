from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from company.tools.executor import ToolExecutor
from company.tools.models import ToolRequest, ToolResult
from company.tools.registry import ToolRegistry


@dataclass(frozen=True)
class AgentToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentToolOutcome:
    call: AgentToolCall
    result: ToolResult


class AgentToolInterface:
    """Provider-independent boundary between agents and M20 tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        executor: ToolExecutor,
    ) -> None:
        self._registry = registry
        self._executor = executor

    def available_tools(self) -> tuple[str, ...]:
        return self._registry.names()

    def execute(
        self,
        call: AgentToolCall,
        *,
        actor: str = "agent",
    ) -> AgentToolOutcome:
        request = ToolRequest(
            tool_name=call.tool_name,
            arguments=dict(call.arguments),
            actor=actor,
        )

        result = self._executor.execute(request)

        return AgentToolOutcome(
            call=call,
            result=result,
        )
