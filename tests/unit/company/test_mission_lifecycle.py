import pytest

from src.company.mission_controller.lifecycle import (
    inspect_mission_lifecycle,
    validate_step_transition,
)
from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission


def test_valid_fresh_plan_has_no_lifecycle_issues():
    plan = build_mission_plan(CompanyMission(name="Fresh", objective="Build an app"))

    result = inspect_mission_lifecycle(plan)

    assert result["valid"] is True
    assert result["issues"] == []
    assert result["stage_count"] == result["expected_stage_count"]
    assert result["planned_stages"][0] == "research"


def test_lifecycle_diagnostics_identify_missing_stage():
    plan = build_mission_plan(CompanyMission(name="Missing", objective="Build an app"))
    plan.steps = plan.steps[:-1]

    result = inspect_mission_lifecycle(plan)

    assert result["valid"] is False
    assert any("missing required lifecycle stage 'learning'" in issue for issue in result["issues"])


def test_lifecycle_diagnostics_identify_multiple_running_stages():
    plan = build_mission_plan(CompanyMission(name="Stuck", objective="Build an app"))
    plan.steps[0].status = "running"
    plan.steps[1].status = "running"

    result = inspect_mission_lifecycle(plan)

    assert result["valid"] is False
    assert any("multiple in-flight stages" in issue for issue in result["issues"])
    assert result["running_stages"] == ["research", "product"]


def test_completed_stage_requires_completed_dependencies():
    plan = build_mission_plan(CompanyMission(name="Inconsistent", objective="Build an app"))
    plan.steps[1].status = "completed"

    result = inspect_mission_lifecycle(plan)

    assert result["valid"] is False
    assert any("incomplete prerequisites: research" in issue for issue in result["issues"])


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("planned", "running"),
        ("running", "completed"),
        ("running", "failed"),
        ("failed", "running"),
    ],
)
def test_allowed_stage_transitions(current, target):
    validate_step_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("planned", "completed"),
        ("completed", "running"),
        ("failed", "completed"),
        ("mystery", "running"),
    ],
)
def test_invalid_stage_transitions_are_rejected(current, target):
    with pytest.raises(ValueError):
        validate_step_transition(current, target)


def test_stage_summary_sanitizes_details_and_preserves_attempt_counts():
    plan = build_mission_plan(CompanyMission(name="Trace", objective="Build an app"))
    plan.steps[0].attempts = 2
    plan.steps[0].detail = "provider failed: password=hiddenSecret123"

    result = inspect_mission_lifecycle(plan)
    summary = result["stage_summary"][0]

    assert summary["stage"] == "research"
    assert summary["attempts"] == 2
    assert "hiddenSecret123" not in summary["detail"]
    assert "password=[REDACTED]" in summary["detail"]
