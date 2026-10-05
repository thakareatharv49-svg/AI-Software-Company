from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from company.ai.context import AIExecutionContext
from company.ai.tool_calling import (
    AIToolCallingEngine,
    AIToolCallResponse,
    AIToolExchange,
)


@dataclass(frozen=True)
class AIToolLoopResult:
    """Result of one bounded AI tool-calling loop."""

    response: AIToolCallResponse
    exchanges: tuple[AIToolExchange, ...]
    rounds: int
    stopped_by_limit: bool


class AIToolCallingLoop:
    """Bounded orchestration loop around the M22 tool boundary."""

    def __init__(self, engine: AIToolCallingEngine) -> None:
        self._engine = engine

    def run(
        self,
        initial_response: AIToolCallResponse,
        *,
        context: AIExecutionContext,
        next_response: Callable[
            [AIToolCallResponse, tuple[AIToolExchange, ...]],
            AIToolCallResponse,
        ] | None = None,
    ) -> AIToolLoopResult:
        current = initial_response
        exchanges: list[AIToolExchange] = []
        rounds = 0
        tool_calls = 0

        while current.tool_calls:
            if rounds >= context.max_rounds:
                return AIToolLoopResult(
                    response=current,
                    exchanges=tuple(exchanges),
                    rounds=rounds,
                    stopped_by_limit=True,
                )

            remaining = context.max_tool_calls - tool_calls

            if remaining <= 0:
                return AIToolLoopResult(
                    response=current,
                    exchanges=tuple(exchanges),
                    rounds=rounds,
                    stopped_by_limit=True,
                )

            requested_count = len(current.tool_calls)
            calls = current.tool_calls[:remaining]
            was_truncated = len(calls) < requested_count

            exchange_batch = self._engine.execute_response(
                AIToolCallResponse(
                    text=current.text,
                    tool_calls=calls,
                ),
                actor=context.actor,
            )

            exchanges.extend(exchange_batch)
            tool_calls += len(exchange_batch)
            rounds += 1

            if was_truncated or tool_calls >= context.max_tool_calls:
                return AIToolLoopResult(
                    response=current,
                    exchanges=tuple(exchanges),
                    rounds=rounds,
                    stopped_by_limit=True,
                )

            if next_response is None:
                return AIToolLoopResult(
                    response=current,
                    exchanges=tuple(exchanges),
                    rounds=rounds,
                    stopped_by_limit=False,
                )

            current = next_response(
                current,
                tuple(exchange_batch),
            )

        return AIToolLoopResult(
            response=current,
            exchanges=tuple(exchanges),
            rounds=rounds,
            stopped_by_limit=False,
        )
