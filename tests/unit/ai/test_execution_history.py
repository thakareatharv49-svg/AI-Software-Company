from __future__ import annotations

from pathlib import Path

from company.ai.history import (
    AIExecutionHistoryRecord,
    AIExecutionHistoryStore,
)
from company.ai.observability import AIExecutionObservation


def make_observation(
    *,
    run_id: str,
    actor: str = "ai",
    success: bool = True,
) -> AIExecutionObservation:
    return AIExecutionObservation(
        run_id=run_id,
        actor=actor,
        rounds=2,
        tool_calls=3,
        stopped_by_limit=False,
        success=success,
        timestamp="2026-10-05T12:00:00+00:00",
    )


def test_history_record_is_created_from_observation() -> None:
    observation = make_observation(run_id="run-1")

    record = AIExecutionHistoryRecord.from_observation(observation)

    assert record.run_id == "run-1"
    assert record.actor == "ai"
    assert record.rounds == 2
    assert record.tool_calls == 3
    assert record.success is True


def test_history_store_persists_and_reloads_records(tmp_path: Path) -> None:
    path = tmp_path / "execution_history.jsonl"

    first_store = AIExecutionHistoryStore(path)
    observation = make_observation(run_id="run-1", actor="ai-ceo")

    written = first_store.append(observation)

    second_store = AIExecutionHistoryStore(path)
    records = second_store.list()

    assert written == records[0]
    assert second_store.get("run-1") == written
    assert second_store.latest() == written


def test_history_store_filters_by_run_and_actor(tmp_path: Path) -> None:
    store = AIExecutionHistoryStore(tmp_path / "history.jsonl")

    first = make_observation(run_id="run-1", actor="ai")
    second = make_observation(run_id="run-2", actor="ai-ceo")
    third = make_observation(run_id="run-3", actor="ai")

    store.append(first)
    store.append(second)
    store.append(third)

    assert len(store.list(run_id="run-2")) == 1
    assert store.list(run_id="run-2")[0].run_id == "run-2"
    assert len(store.list(actor="ai")) == 2
    assert len(store.list(actor="ai-ceo")) == 1


def test_history_store_returns_empty_when_file_does_not_exist(
    tmp_path: Path,
) -> None:
    store = AIExecutionHistoryStore(tmp_path / "missing.jsonl")

    assert store.list() == ()
    assert store.get("missing") is None
    assert store.latest() is None


def test_history_persists_only_execution_metadata(tmp_path: Path) -> None:
    store = AIExecutionHistoryStore(tmp_path / "history.jsonl")

    observation = make_observation(run_id="secure-run")
    store.append(observation)

    raw = (tmp_path / "history.jsonl").read_text(encoding="utf-8")

    assert "secure-run" in raw
    assert "tool_calls" in raw
    assert "arguments" not in raw
    assert "output" not in raw
    assert "error" not in raw
