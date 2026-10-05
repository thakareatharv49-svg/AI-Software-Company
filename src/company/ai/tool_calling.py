from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from company.agents.tool_integration import build_safe_agent_tool_runner
from company.agents.tool_runner import AgentToolRequest


@dataclass(frozen=True)
class AIToolCall:
    """Provider-independent tool call requested by an AI model."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "arguments",
            dict(self.arguments),
        )


@dataclass(frozen=True)
class AIToolCallResult:
    """Result returned to the AI layer after tool execution."""

    tool_name: str
    status: str
    output: Any = None
    error: str | None = None


@dataclass(frozen=True)
class AIToolExchange:
    """Complete AI tool-call exchange."""

    call: AIToolCall
    result: AIToolCallResult


@dataclass(frozen=True)
class AIToolCallResponse:
    """Model response containing zero or more tool calls."""

    text: str = ""
    tool_calls: tuple[AIToolCall, ...] = ()


class AIToolCallTranslator:
    """Translate between AI tool calls and M21 agent requests."""

    @staticmethod
    def to_agent_request(call: AIToolCall) -> AgentToolRequest:
        return AgentToolRequest(
            tool_name=call.tool_name,
            arguments=dict(call.arguments),
        )

    @staticmethod
    def from_agent_execution(
        call: AIToolCall,
        execution: Any,
    ) -> AIToolCallResult:
        result = execution.outcome.result

        return AIToolCallResult(
            tool_name=call.tool_name,
            status=result.status.value,
            output=result.output,
            error=result.error,
        )


class AIToolCallingEngine:
    """Provider-independent AI-to-M21 tool execution boundary."""

    def __init__(self, runner: Any) -> None:
        self._runner = runner

    def available_tools(self) -> tuple[str, ...]:
        return self._runner.list_tools()

    def execute_call(
        self,
        call: AIToolCall,
        *,
        actor: str = "ai",
    ) -> AIToolExchange:
        request = AIToolCallTranslator.to_agent_request(call)

        execution = self._runner.run(
            request,
            actor=actor,
        )

        result = AIToolCallTranslator.from_agent_execution(
            call,
            execution,
        )

        return AIToolExchange(
            call=call,
            result=result,
        )

    def execute_response(
        self,
        response: AIToolCallResponse,
        *,
        actor: str = "ai",
    ) -> tuple[AIToolExchange, ...]:
        return tuple(
            self.execute_call(
                call,
                actor=actor,
            )
            for call in response.tool_calls
        )


def build_ai_tool_calling_engine() -> AIToolCallingEngine:
    """Build the safe M22 AI-to-tool execution boundary."""

    return AIToolCallingEngine(
        build_safe_agent_tool_runner()
    )
