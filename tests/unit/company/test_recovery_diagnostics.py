import pytest

from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.recovery_diagnostics import build_recovery_diagnostics


def make_steps():
    return build_mission_plan(
        CompanyMission(name="Recovery", objective="Diagnose mission recovery")
    ).steps


@pytest.mark.parametrize(
    ("status", "expected_action", "safe"),
    [
        ("completed", "none_completed", False),
        ("blocked", "inspect_error_then_explicitly_retry", False),
        ("failed", "inspect_error_then_explicitly_retry", False),
        ("cancelled", "resume_after_recovery_state_check", False),
        ("queued", "resume_from_last_safe_stage", True),
    ],
)
def test_recovery_diagnostics_recommends_conservative_action(status, expected_action, safe):
    result = build_recovery_diagnostics(
        status=status,
        last_error="provider failed",
        attempts=2,
        steps=make_steps(),
        queue_depth=3,
    )

    assert result["recommended_action"] == expected_action
    assert result["safe_to_retry_automatically"] is safe
    assert result["attempts"] == 2
    assert result["queue_depth"] == 3


def test_recovery_diagnostics_identifies_failed_stage_and_bounds_detail():
    steps = make_steps()
    steps[0].status = "completed"
    steps[1].status = "failed"
    steps[1].detail = "failure detail " * 100

    result = build_recovery_diagnostics(
        status="blocked",
        last_error="bad generated code",
        attempts=-4,
        steps=steps,
        queue_depth=-1,
    )

    assert result["blocking_stage"] == steps[1].stage.value
    assert result["blocking_stage_status"] == "failed"
    assert len(result["stage_detail"]) <= 500
    assert result["attempts"] == 0
    assert result["queue_depth"] == 0


def test_running_stage_recommends_heartbeat_check_not_blind_retry():
    steps = make_steps()
    steps[0].status = "completed"
    steps[1].status = "running"

    result = build_recovery_diagnostics(
        status="running",
        last_error=None,
        attempts=1,
        steps=steps,
        queue_depth=0,
    )

    assert result["blocking_stage"] == steps[1].stage.value
    assert result["recommended_action"] == "check_worker_heartbeat_before_restarting"
    assert result["safe_to_retry_automatically"] is False


def test_failed_stage_takes_priority_over_later_planned_stages():
    steps = make_steps()
    steps[0].status = "failed"
    steps[1].status = "planned"

    result = build_recovery_diagnostics(
        status="blocked",
        last_error=None,
        attempts=1,
        steps=steps,
        queue_depth=0,
    )

    assert result["blocking_stage_status"] == "failed"
    assert result["blocking_stage"] == steps[0].stage.value
