"""Lifecycle invariants shared by execution and mission diagnostics."""

from collections import Counter

from src.company.mission_controller.models import MissionPlan, MissionStage
from src.company.mission_controller.planner import validate_mission_plan
from src.security.redaction import redact_sensitive_text

_ALLOWED_STEP_STATUSES = frozenset({"planned", "running", "completed", "failed"})
_ALLOWED_STEP_TRANSITIONS = {
    "planned": frozenset({"running"}),
    "running": frozenset({"completed", "failed"}),
    "failed": frozenset({"running"}),
    "completed": frozenset(),
}


def validate_step_transition(current: str, target: str) -> None:
    """Reject impossible in-memory stage transitions with an actionable error."""
    if current not in _ALLOWED_STEP_STATUSES:
        raise ValueError(f"Unknown mission stage status: {current!r}")
    if target not in _ALLOWED_STEP_TRANSITIONS[current]:
        raise ValueError(f"Invalid mission stage transition: {current} -> {target}")


def inspect_mission_lifecycle(plan: MissionPlan) -> dict[str, object]:
    """Return stable, actionable structural and runtime lifecycle diagnostics."""
    issues = list(validate_mission_plan(plan))
    stages = [step.stage.value for step in plan.steps]
    counts = Counter(stages)
    expected = {stage.value for stage in MissionStage}
    for missing in sorted(expected - set(stages)):
        issues.append(f"Mission plan is missing required lifecycle stage '{missing}'.")
    for duplicate, count in sorted(counts.items()):
        if count > 1:
            issues.append(f"Mission plan repeats lifecycle stage '{duplicate}' ({count} times).")

    invalid = [
        f"{step.stage.value}={step.status!r}"
        for step in plan.steps
        if str(getattr(step.status, "value", step.status)).casefold()
        not in _ALLOWED_STEP_STATUSES
    ]
    if invalid:
        issues.append("Mission plan has unknown stage status values: " + ", ".join(invalid))

    running = [
        step.stage.value for step in plan.steps
        if str(getattr(step.status, "value", step.status)).casefold() == "running"
    ]
    if len(running) > 1:
        issues.append(
            "Mission plan has multiple in-flight stages: " + ", ".join(running) + "."
        )

    completed = {
        step.stage.value for step in plan.steps
        if str(getattr(step.status, "value", step.status)).casefold() == "completed"
    }
    for step in plan.steps:
        status = str(getattr(step.status, "value", step.status)).casefold()
        if status != "completed":
            continue
        missing = sorted(set(step.depends_on) - completed)
        if missing:
            issues.append(
                f"Completed stage '{step.stage.value}' has incomplete prerequisites: "
                + ", ".join(missing) + "."
            )

    return {
        "valid": not issues,
        "issues": list(dict.fromkeys(issues)),
        "stage_count": len(plan.steps),
        "expected_stage_count": len(MissionStage),
        "completed_stages": len(completed),
        "running_stages": running,
        "failed_stages": [
            step.stage.value for step in plan.steps
            if str(getattr(step.status, "value", step.status)).casefold() == "failed"
        ],
        "planned_stages": [
            step.stage.value for step in plan.steps
            if str(getattr(step.status, "value", step.status)).casefold() == "planned"
        ],
        "stage_summary": [
            {
                "stage": step.stage.value,
                "status": str(getattr(step.status, "value", step.status)).casefold(),
                "attempts": max(0, min(1_000_000, int(step.attempts or 0))),
                "detail": (
                    redact_sensitive_text(str(step.detail))[:1000]
                    if step.detail else None
                ),
            }
            for step in plan.steps
        ],
    }
