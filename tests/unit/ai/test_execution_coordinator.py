from __future__ import annotations

from pathlib import Path

from company.ai.context import AIExecutionContext
from company.ai.coordinator import (
    AIExecutionCoordinator,
    build_ai_execution_coordinator,
)
from company.ai.history import AIExecutionHistoryStore
from company.ai.observability import AIExecutionObserver
from company.ai.runtime import build_ai_execution_runtime
from company.ai.tool_calling import AIToolCall, AIToolCallResponse


def test_coordinator_executes_and_persists_history(tmp_path: Path) -> None:
    history_path = tmp_path / "execution_history.jsonl"

    coordinator = build_ai_execution_coordinator(history_path)

    result = coordinator.execute(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "run"}),
            )
        ),
        context=AIExecutionContext(actor="ai"),
    )

    record = coordinator.history.get(result.run_id)

    assert record is not None
    assert record.run_id == result.run_id
    assert record.actor == "ai"
    assert record.rounds == result.loop.rounds
    assert record.tool_calls == len(result.loop.exchanges)


def test_coordinator_history_survives_new_coordinator_instance(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "execution_history.jsonl"

    first = build_ai_execution_coordinator(history_path)

    result = first.execute(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "persist"}),
            )
        ),
        context=AIExecutionContext(actor="ai"),
    )

    second = build_ai_execution_coordinator(history_path)

    record = second.history.get(result.run_id)

    assert record is not None
    assert record.run_id == result.run_id


def test_coordinator_uses_observer_and_history(
    tmp_path: Path,
) -> None:
    history = AIExecutionHistoryStore(tmp_path / "history.jsonl")

    coordinator = AIExecutionCoordinator(
        runtime=build_ai_execution_runtime(),
        observer=AIExecutionObserver(),
        history=history,
    )

    result = coordinator.execute(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "observed"}),
            )
        ),
        context=AIExecutionContext(actor="ai-ceo"),
    )

    records = history.list()

    assert len(records) == 1
    assert records[0].run_id == result.run_id
    assert records[0].actor == "ai-ceo"


def test_coordinator_exposes_persistent_history_store(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "history.jsonl"

    coordinator = build_ai_execution_coordinator(history_path)

    assert coordinator.history.path == history_path
    assert coordinator.history.list() == ()
