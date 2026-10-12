from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from src.company.control_center.routes import mission_diagnostics
from src.company.mission_controller.models import MissionStage
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission


def make_job(status: MissionJobStatus, *, age_seconds: int = 0) -> MissionJob:
    mission = CompanyMission(name="Diagnostics", objective="Build a useful app")
    plan = build_mission_plan(mission)
    if status == MissionJobStatus.RUNNING:
        plan.steps[0].status = "running"
        plan.steps[0].detail = "Executing architecture stage"
    if status in {MissionJobStatus.FAILED, MissionJobStatus.BLOCKED}:
        plan.steps[0].status = "failed"
        plan.steps[0].detail = "Dependency installation failed"
    now = datetime.now(UTC) - timedelta(seconds=age_seconds)
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=status,
        message=f"{status.value} mission",
        attempts=2,
        created_at=now,
        updated_at=now,
    )


class Center:
    def __init__(self, job):
        self.job = job

    def mission_job(self, mission_id):
        return self.job if self.job.id == mission_id else None


def test_diagnostics_flags_old_running_mission_without_claiming_certainty():
    job = make_job(MissionJobStatus.RUNNING, age_seconds=2200)

    result = mission_diagnostics(job.id, Center(job))

    assert result["diagnosis"] == "possibly_stalled"
    assert result["recommended_action"] == "inspect_audit_and_worker_before_retrying"
    assert result["current_stage"] == job.plan.steps[0].stage.value
    assert result["failure_detail"] is None
    assert "may also delay updates" in result["message"]


def test_diagnostics_marks_recent_running_mission_active():
    job = make_job(MissionJobStatus.RUNNING, age_seconds=60)

    result = mission_diagnostics(job.id, Center(job))

    assert result["diagnosis"] == "active"
    assert result["recommended_action"] == "continue_monitoring"


def test_diagnostics_explains_queued_mission_waiting_for_worker():
    job = make_job(MissionJobStatus.QUEUED, age_seconds=600)

    result = mission_diagnostics(job.id, Center(job))

    assert result["diagnosis"] == "waiting_for_worker"
    assert result["recommended_action"] == "start_or_check_factory_worker"


def test_diagnostics_surfaces_failed_stage_and_action():
    job = make_job(MissionJobStatus.FAILED)

    result = mission_diagnostics(job.id, Center(job))

    assert result["diagnosis"] == "failed"
    assert result["failed_stage"] == job.plan.steps[0].stage.value
    assert result["failure_detail"] == "Dependency installation failed"
    assert result["recommended_action"] == "review_failure_details_then_retry"


def test_diagnostics_returns_404_for_unknown_mission():
    from uuid import uuid4

    missing_id = str(uuid4())
    job = make_job(MissionJobStatus.QUEUED)

    try:
        mission_diagnostics(missing_id, Center(job))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected missing mission to return 404")
