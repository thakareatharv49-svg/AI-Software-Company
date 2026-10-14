"""Regression tests for best-effort, per-snapshot factory recovery persistence."""

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        return ModelResponse(content="stage completed", model="fake", provider="fake")


def make_factory(store, job_store=None):
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    return ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        store=store,
        job_store=job_store,
    )


def snapshot(mission, status="queued"):
    return {
        "mission": mission,
        "plan": build_mission_plan(mission),
        "status": status,
        "attempts": 0,
        "stages_executed": 0,
    }


class SnapshotStore:
    def __init__(self, pending):
        self.pending = pending
        self.saved = []
        self.deleted = []

    def load_pending(self):
        return self.pending

    def save(self, project):
        self.saved.append(project.mission.id)

    def delete_many(self, mission_ids):
        self.deleted.extend(mission_ids)


def test_restore_isolates_snapshot_write_failures_and_deduplicates_ids():
    first = CompanyMission(name="First", objective="Recover despite a write failure")
    second = CompanyMission(name="Second", objective="Recover independently")
    store = SnapshotStore([snapshot(first), snapshot(first), snapshot(second)])
    original_save = store.save

    def fail_first_mission(project):
        if project.mission.id == first.id:
            raise OSError("temporary snapshot write failure")
        original_save(project)

    store.save = fail_first_mission
    factory = make_factory(store)

    assert factory.restore() == 2
    assert [project.mission.id for project in factory.queue] == [first.id, second.id]


def test_restore_does_not_resurrect_terminal_job_when_snapshot_delete_fails():
    terminal = CompanyMission(name="Finished", objective="Do not restore completed work")
    later = CompanyMission(name="Later", objective="Continue after cleanup failure")
    store = SnapshotStore([snapshot(terminal), snapshot(later)])
    store.delete_many = lambda _ids: (_ for _ in ()).throw(OSError("delete failed"))

    class JobStore:
        def get(self, job_id):
            if job_id != terminal.id:
                return None
            return MissionJob(
                id=terminal.id,
                mission=terminal,
                plan=build_mission_plan(terminal),
                status=MissionJobStatus.COMPLETED,
                message="completed",
            )

        def save(self, _job):
            pass

    factory = make_factory(store, JobStore())

    assert factory.restore() == 1
    assert [project.mission.id for project in factory.queue] == [later.id]


def test_restore_skips_running_snapshot_if_recovery_job_write_fails_but_continues():
    interrupted = CompanyMission(name="Interrupted", objective="Recover durable state")
    later = CompanyMission(name="Later", objective="Must still be restored")
    store = SnapshotStore([snapshot(interrupted, status="running"), snapshot(later)])

    class JobStore:
        def get(self, job_id):
            if job_id != interrupted.id:
                return None
            return MissionJob(
                id=interrupted.id,
                mission=interrupted,
                plan=build_mission_plan(interrupted),
                status=MissionJobStatus.RUNNING,
                message="running",
            )

        def save(self, _job):
            raise OSError("durable job store unavailable")

    factory = make_factory(store, JobStore())

    assert factory.restore() == 1
    assert [project.mission.id for project in factory.queue] == [later.id]
