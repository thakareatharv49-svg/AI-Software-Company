from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from company.ai.context import AIExecutionContext
from company.ai.loop import AIToolCallingLoop, AIToolLoopResult
from company.ai.tool_calling import (
    AIToolCallingEngine,
    AIToolCallResponse,
    build_ai_tool_calling_engine,
)


@dataclass(frozen=True)
class AIExecutionResult:
    """Top-level result returned by the AI execution runtime."""

    run_id: str
    actor: str
    loop: AIToolLoopResult


class AIExecutionRuntime:
    """Provider-independent runtime for bounded AI tool execution."""

    def __init__(self, engine: AIToolCallingEngine) -> None:
        self._loop = AIToolCallingLoop(engine)

    def execute(
        self,
        initial_response: AIToolCallResponse,
        *,
        context: AIExecutionContext,
        next_response: Callable[..., AIToolCallResponse] | None = None,
    ) -> AIExecutionResult:
        result = self._loop.run(
            initial_response,
            context=context,
            next_response=next_response,
        )

        return AIExecutionResult(
            run_id=context.run_id,
            actor=context.actor,
            loop=result,
        )


def build_ai_execution_runtime() -> AIExecutionRuntime:
    """Build the default safe AI execution runtime."""
    return AIExecutionRuntime(build_ai_tool_calling_engine())


def execute_ai_response(
    response: AIToolCallResponse,
    *,
    actor: str = "ai",
    metadata: dict[str, Any] | None = None,
    max_tool_calls: int = 10,
    max_rounds: int = 5,
) -> AIExecutionResult:
    """Execute one AI response with bounded tool execution."""

    context = AIExecutionContext(
        actor=actor,
        metadata=metadata or {},
        max_tool_calls=max_tool_calls,
        max_rounds=max_rounds,
    )

    return build_ai_execution_runtime().execute(
        response,
        context=context,
    )
