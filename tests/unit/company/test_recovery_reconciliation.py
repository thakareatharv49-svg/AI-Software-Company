from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import FactoryProject, ProjectFactory


def make_job(status=MissionJobStatus.QUEUED):
    mission = CompanyMission(name="Reconcile", objective="Check recovery state consistency")
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=status,
        message="reconciliation test",
    )


class SnapshotStore:
    def __init__(self, records=None, *, fail=False):
        self.records = list(records or [])
        self.fail = fail
        self.saved = []

    def load_pending(self):
        if self.fail:
            raise OSError("snapshot store offline")
        return list(self.records)

    def save(self, project):
        if self.fail:
            raise OSError("snapshot store offline")
        self.saved.append(project)
        self.records = [
            item for item in self.records
            if item.get("mission").id != project.mission.id
        ]
        self.records.append({
            "mission": project.mission,
            "plan": project.plan,
            "status": project.status,
            "attempts": project.attempts,
        })


def make_factory(job, store=None, queue=None):
    factory = object.__new__(ProjectFactory)
    factory.queue = list(queue or [])
    factory.store = store
    factory.job_store = object()
    factory._running = False
    factory._active_project = None
    factory._load_job = lambda _mission_id: job
    factory._save = lambda project: store.save(project) if store else None
    factory.audits = []
    factory._audit = lambda *args, **kwargs: factory.audits.append((args, kwargs))
    return factory


def test_reconcile_is_read_only_by_default():
    job = make_job()
    store = SnapshotStore()
    factory = make_factory(job, store)

    result = factory.reconcile_mission(job.id)

    assert result["consistent"] is False
    assert "durable_queued_job_missing_from_memory_queue" in result["discrepancies"]
    assert factory.queue == []
    assert store.saved == []


def test_reconcile_repairs_only_missing_queue_entry_from_durable_queued_job():
    job = make_job()
    store = SnapshotStore()
    factory = make_factory(job, store)

    result = factory.reconcile_mission(job.id, repair=True)

    assert result["repair_attempted"] is True
    assert len(factory.queue) == 1
    assert factory.queue[0].mission.id == job.id
    assert len(store.saved) == 1
    assert result["consistent"] is False  # verification is required after repair


def test_reconcile_withholds_repair_when_snapshot_plan_conflicts():
    job = make_job()
    conflicting_plan = build_mission_plan(
        CompanyMission(name="Different", objective="Conflicting persisted plan")
    )
    store = SnapshotStore([{
        "mission": job.mission,
        "plan": conflicting_plan,
        "status": "queued",
        "attempts": 0,
    }])
    factory = make_factory(job, store)

    result = factory.reconcile_mission(job.id, repair=True)

    assert "project_snapshot_plan_differs_from_durable_job" in result["discrepancies"]
    assert factory.queue == []
    assert store.saved == []


def test_reconcile_reports_duplicate_queue_entries_without_mutating_them():
    job = make_job()
    project = FactoryProject(mission=job.mission, plan=job.plan)
    factory = make_factory(job, queue=[project, project])

    result = factory.reconcile_mission(job.id)

    assert "duplicate_in_memory_queue_entries" in result["discrepancies"]
    assert len(factory.queue) == 2


def test_reconcile_reports_missing_durable_job():
    factory = make_factory(None)

    result = factory.reconcile_mission("missing-id")

    assert result["discrepancies"] == ["durable_job_missing"]
    assert result["repair_attempted"] is False


def test_reconcile_refuses_repair_while_worker_active():
    job = make_job()
    factory = make_factory(job)
    factory._running = True

    try:
        factory.reconcile_mission(job.id, repair=True)
    except RuntimeError as exc:
        assert "worker is active" in str(exc)
    else:
        raise AssertionError("expected active worker guard")
