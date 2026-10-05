import pytest

from src.company.mission_jobs import MissionJob, MissionJobStatus, transition_job
from src.company.models.contracts import CompanyMission
from src.company.mission_controller.planner import build_mission_plan


def make_job(status: MissionJobStatus = MissionJobStatus.QUEUED) -> MissionJob:
    mission = CompanyMission(name="Lifecycle", objective="Track lifecycle")
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=status,
        message="created",
    )


def test_job_lifecycle_allows_queue_run_complete() -> None:
    job = make_job()
    job = transition_job(job, MissionJobStatus.RUNNING, "started")
    job = transition_job(job, MissionJobStatus.COMPLETED, "done")

    assert job.status == MissionJobStatus.COMPLETED
    assert job.message == "done"


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (MissionJobStatus.COMPLETED, MissionJobStatus.RUNNING),
        (MissionJobStatus.CANCELLED, MissionJobStatus.QUEUED),
        (MissionJobStatus.QUEUED, MissionJobStatus.COMPLETED),
    ],
)
def test_job_lifecycle_rejects_invalid_transitions(
    source: MissionJobStatus,
    target: MissionJobStatus,
) -> None:
    with pytest.raises(ValueError, match="Invalid mission transition"):
        transition_job(make_job(source), target, "invalid")


def test_failed_job_can_be_requeued() -> None:
    job = transition_job(make_job(), MissionJobStatus.RUNNING, "started")
    job = transition_job(job, MissionJobStatus.FAILED, "temporary failure")
    job = transition_job(job, MissionJobStatus.QUEUED, "retry")

    assert job.status == MissionJobStatus.QUEUED


def test_running_job_recovers_to_queued() -> None:
    from src.company.mission_jobs import recover_running_job
    recovered = recover_running_job(make_job(MissionJobStatus.RUNNING))
    assert recovered.status == MissionJobStatus.QUEUED
    assert "restart" in recovered.message.lower()


def test_recovery_does_not_change_non_running_job() -> None:
    from src.company.mission_jobs import recover_running_job
    job = make_job(MissionJobStatus.BLOCKED)
    assert recover_running_job(job) == job
