from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus, transition_job
from src.company.persistence import MissionJobRow, MissionJobStore
from src.company.models.contracts import CompanyMission
from src.db.base import Base


def make_job(name: str, status: MissionJobStatus = MissionJobStatus.QUEUED) -> MissionJob:
    mission = CompanyMission(name=name, objective=f"Persist {name}")
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=MissionJobStatus.QUEUED,
        message="created",
        workspace_id=None,
    )
    if status != MissionJobStatus.QUEUED:
        job = transition_job(job, status, f"state={status.value}")
    return job


def make_store(tmp_path, monkeypatch) -> MissionJobStore:
    database_path = tmp_path / "mission-jobs.sqlite"
    monkeypatch.setattr(
        "src.company.persistence.settings.database_url",
        f"sqlite:///{database_path.as_posix()}",
    )
    store = MissionJobStore()
    Base.metadata.create_all(store._engine, tables=[MissionJobRow.__table__])
    return store


def test_mission_job_store_round_trips_lifecycle_and_workspace(tmp_path, monkeypatch) -> None:
    store = make_store(tmp_path, monkeypatch)
    try:
        queued = make_job("Queued")
        running = transition_job(queued, MissionJobStatus.RUNNING, "worker started")
        running = running.model_copy(update={"workspace_id": None, "attempts": 3})
        store.save(running)

        restored = store.get(running.id)
        assert restored is not None
        assert restored.status == MissionJobStatus.RUNNING
        assert restored.attempts == 3
        assert restored.workspace_id is None
        assert restored.mission.name == "Queued"
        assert restored.plan.steps[0].status == running.plan.steps[0].status
    finally:
        store.close()


def test_mission_job_store_recovers_running_job_and_preserves_completed_work(
    tmp_path, monkeypatch
) -> None:
    store = make_store(tmp_path, monkeypatch)
    try:
        job = make_job("Restart recovery")
        job.plan.steps[0].status = "completed"
        job.plan.steps[0].detail = "verified checkpoint"
        job.plan.steps[1].status = "running"
        job.plan.steps[1].detail = "process stopped mid-stage"
        running = transition_job(job, MissionJobStatus.RUNNING, "worker active")
        store.save(running)

        recovered = store.recover_running()
        assert len(recovered) == 1
        assert recovered[0].status == MissionJobStatus.QUEUED
        assert recovered[0].plan.steps[0].status == "completed"
        assert recovered[0].plan.steps[0].detail == "verified checkpoint"
        assert recovered[0].plan.steps[1].status == "planned"
        assert recovered[0].plan.steps[1].detail is None

        # Verify the recovered state is persisted, not just returned in memory.
        restored = store.get(job.id)
        assert restored is not None
        assert restored.status == MissionJobStatus.QUEUED
        assert restored.plan.steps[0].detail == "verified checkpoint"
    finally:
        store.close()


def test_mission_job_store_recovery_leaves_terminal_jobs_unchanged(
    tmp_path, monkeypatch
) -> None:
    store = make_store(tmp_path, monkeypatch)
    try:
        completed = make_job("Terminal", MissionJobStatus.RUNNING)
        completed = transition_job(completed, MissionJobStatus.COMPLETED, "done")
        store.save(completed)

        assert store.recover_running() == []
        restored = store.get(completed.id)
        assert restored is not None
        assert restored.status == MissionJobStatus.COMPLETED
        assert restored.message == "done"
    finally:
        store.close()
