from __future__ import annotations

from pathlib import Path

from company.ai.context import AIExecutionContext
from company.ai.history import AIExecutionHistoryStore
from company.ai.observability import AIExecutionObserver
from company.ai.runtime import (
    AIExecutionResult,
    AIExecutionRuntime,
    build_ai_execution_runtime,
)


class AIExecutionCoordinator:
    """Coordinates execution, observation, and persistent execution history."""

    def __init__(
        self,
        runtime: AIExecutionRuntime,
        observer: AIExecutionObserver,
        history: AIExecutionHistoryStore,
    ) -> None:
        self._runtime = runtime
        self._observer = observer
        self._history = history

    @property
    def history(self) -> AIExecutionHistoryStore:
        return self._history

    def execute(
        self,
        initial_response,
        *,
        context: AIExecutionContext,
        next_response=None,
    ) -> AIExecutionResult:
        result = self._runtime.execute(
            initial_response,
            context=context,
            next_response=next_response,
        )

        observation = self._observer.observe(result)
        self._history.append(observation)

        return result


def build_ai_execution_coordinator(
    history_path: str | Path,
) -> AIExecutionCoordinator:
    return AIExecutionCoordinator(
        runtime=build_ai_execution_runtime(),
        observer=AIExecutionObserver(),
        history=AIExecutionHistoryStore(history_path),
    )
