
from company.runtime.dashboard import RuntimeDashboard
from company.runtime.observability import RuntimeObservability


def test_dashboard_empty_snapshot():
    observability = RuntimeObservability()
    dashboard = RuntimeDashboard(observability)

    snapshot = dashboard.snapshot("stopped")

    assert snapshot.status == "stopped"
    assert snapshot.events == 0
    assert snapshot.runs == 0
    assert snapshot.completed == 0
    assert snapshot.failed == 0
    assert snapshot.average_duration_seconds == 0.0


def test_dashboard_snapshot():
    observability = RuntimeObservability()

    observability.record(
        "run.started",
        run_id="run-1",
        status="running",
    )
    observability.record(
        "run.completed",
        run_id="run-1",
        status="completed",
        duration_seconds=2.0,
    )
    observability.record(
        "run.started",
        run_id="run-2",
        status="running",
    )
    observability.record(
        "run.failed",
        run_id="run-2",
        status="failed",
        duration_seconds=4.0,
    )

    dashboard = RuntimeDashboard(observability)
    snapshot = dashboard.snapshot()

    assert snapshot.events == 4
    assert snapshot.runs == 2
    assert snapshot.completed == 1
    assert snapshot.failed == 1
    assert snapshot.average_duration_seconds == 3.0


def test_dashboard_dict():
    observability = RuntimeObservability()

    observability.record(
        "run.completed",
        run_id="run-1",
        status="completed",
        duration_seconds=1.5,
    )

    dashboard = RuntimeDashboard(observability)
    result = dashboard.as_dict("healthy")

    assert result == {
        "status": "healthy",
        "events": 1,
        "runs": 1,
        "completed": 1,
        "failed": 0,
        "average_duration_seconds": 1.5,
    }
