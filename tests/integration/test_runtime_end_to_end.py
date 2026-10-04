
from company.runtime.end_to_end import AutonomousExecution


def test_successful_autonomous_execution():
    runtime = AutonomousExecution()

    result = runtime.run(
        "e2e-success",
        lambda: {"message": "success"},
    )

    assert result.status == "completed"
    assert result.result == {"message": "success"}
    assert result.error is None


def test_failed_autonomous_execution():
    runtime = AutonomousExecution()

    def fail():
        raise RuntimeError("simulated failure")

    result = runtime.run("e2e-failure", fail)

    assert result.status == "failed"
    assert result.error == "simulated failure"
    assert result.attempts == 1


def test_dashboard_after_execution():
    runtime = AutonomousExecution()

    runtime.run(
        "e2e-dashboard",
        lambda: "ok",
    )

    dashboard = runtime.dashboard()

    assert dashboard["runs"] == 1
    assert dashboard["events"] == 2
    assert dashboard["completed"] == 1
