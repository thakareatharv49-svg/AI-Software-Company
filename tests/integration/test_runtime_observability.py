
import json

from company.runtime.observability import (
    RuntimeObservability,
    RuntimeOperationTimer,
)


def test_record_event():
    observability = RuntimeObservability()

    event = observability.record(
        "run.started",
        run_id="run-1",
        status="running",
        metadata={"source": "test"},
    )

    assert event.event == "run.started"
    assert event.run_id == "run-1"
    assert event.status == "running"
    assert event.metadata["source"] == "test"


def test_filter_events():
    observability = RuntimeObservability()

    observability.record("run.started", run_id="run-1")
    observability.record("run.completed", run_id="run-1")
    observability.record("run.started", run_id="run-2")

    assert len(observability.events(run_id="run-1")) == 2
    assert len(observability.events(event="run.started")) == 2


def test_count():
    observability = RuntimeObservability()

    observability.record("run.started")
    observability.record("run.started")
    observability.record("run.completed")

    assert observability.count() == 3
    assert observability.count("run.started") == 2


def test_summary():
    observability = RuntimeObservability()

    observability.record(
        "run.completed",
        status="completed",
        duration_seconds=2.0,
    )
    observability.record(
        "run.failed",
        status="failed",
        duration_seconds=4.0,
    )

    summary = observability.summary()

    assert summary["events"] == 2
    assert summary["statuses"] == {
        "completed": 1,
        "failed": 1,
    }
    assert summary["duration_total_seconds"] == 6.0
    assert summary["duration_average_seconds"] == 3.0


def test_operation_timer_records_completion():
    observability = RuntimeObservability()

    with RuntimeOperationTimer(
        observability,
        "pipeline",
        run_id="run-1",
    ):
        pass

    events = observability.events(run_id="run-1")

    assert [event.event for event in events] == [
        "pipeline.started",
        "pipeline.completed",
    ]
    assert events[1].status == "completed"
    assert events[1].duration_seconds is not None


def test_operation_timer_records_failure():
    observability = RuntimeObservability()

    try:
        with RuntimeOperationTimer(
            observability,
            "pipeline",
            run_id="run-1",
        ):
            raise ValueError("boom")
    except ValueError:
        pass

    events = observability.events(run_id="run-1")

    assert events[-1].event == "pipeline.failed"
    assert events[-1].status == "failed"
    assert events[-1].duration_seconds is not None


def test_jsonl_persistence(tmp_path):
    log_path = tmp_path / "runtime.jsonl"
    observability = RuntimeObservability(log_path)

    observability.record(
        "run.completed",
        run_id="run-1",
        status="completed",
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["event"] == "run.completed"
    assert payload["run_id"] == "run-1"


def test_events_are_isolated_from_internal_storage():
    observability = RuntimeObservability()

    observability.record("run.started", run_id="run-1")

    events = observability.events()
    events.clear()

    assert observability.count() == 1
