from __future__ import annotations

import pytest

from src.company.runtime.run_registry import RuntimeRunRegistry, RuntimeRunStatus


def test_registry_creates_unique_queued_runs() -> None:
    registry = RuntimeRunRegistry()

    first = registry.create()
    second = registry.create()

    assert first.run_id != second.run_id
    assert first.status is RuntimeRunStatus.QUEUED
    assert second.status is RuntimeRunStatus.QUEUED


def test_registry_tracks_lifecycle_and_result() -> None:
    registry = RuntimeRunRegistry()
    run = registry.create()

    registry.mark_running(run.run_id)
    registry.mark_completed(run.run_id, {"ok": True})

    stored = registry.get(run.run_id)

    assert stored is not None
    assert stored.status is RuntimeRunStatus.COMPLETED
    assert stored.result == {"ok": True}
    assert stored.error is None


def test_registry_tracks_failure() -> None:
    registry = RuntimeRunRegistry()
    run = registry.create()
    error = RuntimeError("boom")

    registry.mark_failed(run.run_id, error)

    stored = registry.get(run.run_id)

    assert stored is not None
    assert stored.status is RuntimeRunStatus.FAILED
    assert stored.error is error


def test_registry_tracks_cancellation() -> None:
    registry = RuntimeRunRegistry()
    run = registry.create()

    registry.mark_cancelled(run.run_id)

    assert registry.get(run.run_id).status is RuntimeRunStatus.CANCELLED


def test_registry_rejects_unknown_run() -> None:
    registry = RuntimeRunRegistry()

    with pytest.raises(KeyError):
        registry.mark_running("missing")


def test_registry_lists_runs() -> None:
    registry = RuntimeRunRegistry()
    first = registry.create()
    second = registry.create()

    runs = registry.all()

    assert {run.run_id for run in runs} == {first.run_id, second.run_id}
