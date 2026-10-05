from __future__ import annotations

from dataclasses import dataclass, field

from company.ai.tool_calling import (
    AIToolCall,
    AIToolCallingEngine,
    AIToolCallResponse,
    AIToolCallResult,
)


@dataclass(frozen=True)
class AIOrchestrationStep:
    """One deterministic step in an AI tool-calling plan."""

    call: AIToolCall
    result: AIToolCallResult


@dataclass(frozen=True)
class AIOrchestrationResult:
    """Complete orchestration result."""

    text: str
    steps: tuple[AIOrchestrationStep, ...] = field(default_factory=tuple)
    success: bool = True


class AIToolOrchestrator:
    """Execute model tool calls sequentially through the M22 boundary."""

    def __init__(self, engine: AIToolCallingEngine) -> None:
        self._engine = engine

    def available_tools(self) -> tuple[str, ...]:
        return self._engine.available_tools()

    def execute(
        self,
        response: AIToolCallResponse,
        *,
        actor: str = "ai",
    ) -> AIOrchestrationResult:
        exchanges = self._engine.execute_response(
            response,
            actor=actor,
        )

        steps = tuple(
            AIOrchestrationStep(
                call=exchange.call,
                result=exchange.result,
            )
            for exchange in exchanges
        )

        return AIOrchestrationResult(
            text=response.text,
            steps=steps,
            success=all(
                step.result.status == "success"
                for step in steps
            ),
        )


def build_ai_tool_orchestrator() -> AIToolOrchestrator:
    from company.ai.tool_calling import build_ai_tool_calling_engine

    return AIToolOrchestrator(
        build_ai_tool_calling_engine()
    )
