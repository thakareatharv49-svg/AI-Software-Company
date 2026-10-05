from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from company.agents.tools import (
    AgentToolCall,
    AgentToolInterface,
    AgentToolOutcome,
)


@dataclass(frozen=True)
class AgentToolRequest:
    """Immutable snapshot of an agent tool request."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "arguments",
            dict(self.arguments),
        )

    def to_call(self) -> AgentToolCall:
        return AgentToolCall(
            tool_name=self.tool_name,
            arguments=dict(self.arguments),
        )


@dataclass(frozen=True)
class AgentToolExecution:
    request: AgentToolRequest
    outcome: AgentToolOutcome


class AgentToolRunner:
    """Safe execution boundary used by agents."""

    def __init__(self, interface: AgentToolInterface) -> None:
        self._interface = interface

    def list_tools(self) -> tuple[str, ...]:
        return self._interface.available_tools()

    def run(
        self,
        request: AgentToolRequest,
        *,
        actor: str = "agent",
    ) -> AgentToolExecution:
        outcome = self._interface.execute(
            request.to_call(),
            actor=actor,
        )

        return AgentToolExecution(
            request=request,
            outcome=outcome,
        )
