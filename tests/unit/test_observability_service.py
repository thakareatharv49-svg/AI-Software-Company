from src.company.observability.service import ObservabilityService


def test_observability_creates_unique_run_ids() -> None:
    service = ObservabilityService()

    first = service.create_run_id()
    second = service.create_run_id()

    assert first
    assert second
    assert first != second


def test_observability_records_events_and_metrics() -> None:
    service = ObservabilityService()
    run_id = service.create_run_id()

    service.record(
        run_id=run_id,
        event_type="autonomous.run.failed",
        payload={"attempt": 1},
    )
    service.record(
        run_id=run_id,
        event_type="autonomous.run.recovery_available",
        payload={"attempt": 1},
    )
    service.record(
        run_id=run_id,
        event_type="autonomous.run.completed",
        payload={"status": "completed"},
    )

    assert len(service.records(run_id)) == 3
    assert service.metrics(run_id) == {
        "events": 3,
        "failures": 1,
        "recoveries": 1,
        "completed": 1,
    }


def test_observability_exports_records() -> None:
    service = ObservabilityService()
    run_id = service.create_run_id()

    service.record(
        run_id=run_id,
        event_type="project.execution.started",
        project_id="project-1",
        payload={"name": "demo"},
    )

    exported = service.export(run_id)

    assert len(exported) == 1
    assert exported[0]["run_id"] == run_id
    assert exported[0]["event_type"] == "project.execution.started"
    assert exported[0]["project_id"] == "project-1"
    assert exported[0]["payload"]["name"] == "demo"
    assert exported[0]["record_id"]
    assert exported[0]["timestamp"]


def test_observability_filters_records_by_run() -> None:
    service = ObservabilityService()
    first = service.create_run_id()
    second = service.create_run_id()

    service.record(run_id=first, event_type="first")
    service.record(run_id=second, event_type="second")

    assert [r.event_type for r in service.records(first)] == ["first"]
    assert [r.event_type for r in service.records(second)] == ["second"]
    assert len(service.records()) == 2


def test_observability_clear() -> None:
    service = ObservabilityService()
    run_id = service.create_run_id()

    service.record(run_id=run_id, event_type="event")
    service.clear()

    assert service.records() == []
    assert service.metrics(run_id) == {
        "events": 0,
        "failures": 0,
        "recoveries": 0,
        "completed": 0,
    }
