import pytest

from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import FactoryProject, ProjectFactory


def make_job(status=MissionJobStatus.QUEUED):
    mission = CompanyMission(name="Recovery action", objective="Safely recover queued work")
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=status,
        message="test state",
    )


def make_factory(job, *, save=None):
    factory = object.__new__(ProjectFactory)
    factory.queue = []
    factory._running = False
    factory._active_project = None
    factory._load_job = lambda _mission_id: job
    factory._save = save or (lambda _project: None)
    factory.audits = []
    factory._audit = lambda *args, **kwargs: factory.audits.append((args, kwargs))
    return factory


def test_resume_rehydrates_only_durably_queued_mission():
    job = make_job()
    factory = make_factory(job)

    result = factory.recover_mission(job.id, "resume")

    assert result["changed"] is True
    assert result["recommended_action"] == "run_queued_mission"
    assert len(factory.queue) == 1
    assert factory.queue[0].mission.id == job.id
    assert factory.queue[0].plan is not job.plan


def test_resume_is_idempotent_when_mission_already_queued():
    job = make_job()
    factory = make_factory(job)
    existing = FactoryProject(mission=job.mission, plan=job.plan)
    factory.queue.append(existing)

    result = factory.recover_mission(job.id, "resume")

    assert result["changed"] is False
    assert len(factory.queue) == 1
    assert factory.queue[0] is existing


@pytest.mark.parametrize("status", [MissionJobStatus.RUNNING, MissionJobStatus.COMPLETED, MissionJobStatus.CANCELLED])
def test_resume_rejects_nonqueued_durable_status(status):
    job = make_job(status)
    factory = make_factory(job)

    with pytest.raises(ValueError, match="only durably queued"):
        factory.recover_mission(job.id, "resume")

    assert factory.queue == []


def test_resume_does_not_queue_when_snapshot_persistence_fails():
    job = make_job()

    def fail_save(_project):
        raise OSError("durable store unavailable")

    factory = make_factory(job, save=fail_save)

    with pytest.raises(OSError, match="durable store unavailable"):
        factory.recover_mission(job.id, "resume")

    assert factory.queue == []


def test_inspect_is_read_only_and_recommends_retry_for_blocked_mission():
    job = make_job(MissionJobStatus.BLOCKED)
    factory = make_factory(job)

    result = factory.recover_mission(job.id, "inspect")

    assert result["recommended_action"] == "retry"
    assert result["changed"] is False
    assert factory.queue == []
    assert factory.audits == []


def test_retry_action_requires_failed_or_blocked_status():
    job = make_job(MissionJobStatus.QUEUED)
    factory = make_factory(job)

    with pytest.raises(ValueError, match="cannot be retried"):
        factory.recover_mission(job.id, "retry")


def test_recovery_rejects_unknown_action_and_active_worker():
    job = make_job()
    factory = make_factory(job)

    with pytest.raises(ValueError, match="Recovery action"):
        factory.recover_mission(job.id, "force")

    factory._running = True
    with pytest.raises(RuntimeError, match="worker is active"):
        factory.recover_mission(job.id, "resume")
