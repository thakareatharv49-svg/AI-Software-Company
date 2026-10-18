"""Actionable, bounded diagnostics for mission recovery decisions."""

from __future__ import annotations

from typing import Any


def build_recovery_diagnostics(
    *,
    status: str,
    last_error: str | None,
    attempts: int,
    steps: list[Any],
    queue_depth: int,
) -> dict[str, Any]:
    """Summarize the first failed/in-flight stage and a conservative next action."""
    normalized_status = str(status or "").strip().lower()
    failed = next(
        (step for step in steps if str(getattr(step, "status", "")).lower() == "failed"),
        None,
    )
    running = next(
        (step for step in steps if str(getattr(step, "status", "")).lower() == "running"),
        None,
    )
    planned = next(
        (step for step in steps if str(getattr(step, "status", "")).lower() == "planned"),
        None,
    )
    active = failed or running or planned
    stage = getattr(getattr(active, "stage", None), "value", getattr(active, "stage", None))
    stage_status = str(getattr(active, "status", "")) if active is not None else None
    detail = getattr(active, "detail", None) if active is not None else None

    if normalized_status == "completed":
        action, safe_to_retry = "none_completed", False
    elif normalized_status in {"blocked", "failed"}:
        action, safe_to_retry = "inspect_error_then_explicitly_retry", False
    elif normalized_status in {"cancelled", "canceled"}:
        action, safe_to_retry = "resume_after_recovery_state_check", False
    elif running is not None:
        action, safe_to_retry = "check_worker_heartbeat_before_restarting", False
    elif planned is not None or failed is not None:
        action, safe_to_retry = "resume_from_last_safe_stage", True
    else:
        action, safe_to_retry = "inspect_mission_state", False

    return {
        "status": normalized_status or "unknown",
        "attempts": max(0, int(attempts)),
        "queue_depth": max(0, int(queue_depth)),
        "blocking_stage": str(stage)[:100] if stage is not None else None,
        "blocking_stage_status": stage_status,
        "stage_detail": str(detail)[:500] if detail else None,
        "error_summary": str(last_error)[:500] if last_error else None,
        "safe_to_retry_automatically": safe_to_retry,
        "recommended_action": action,
    }
