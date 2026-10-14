"""Recovery tests for durable jobs whose project snapshots are missing."""

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MAX_MISSION_ATTEMPTS, MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        return ModelResponse(content="ok", model="fake", provider="fake")


class JobStore:
    def __init__(self, jobs):
        self.jobs = {job.id: job for job in jobs}

    def get(self, job_id):
        return self.jobs.get(job_id)

    def save(self, job):
        self.jobs[job.id] = job

    def list_all(self):
        return list(self.jobs.values())


class BrokenProjectStore:
    def load_pending(self):
        raise OSError("project snapshot store unavailable")

    def save(self, _project):
        raise OSError("project snapshot store unavailable")


def make_job(name, status=MissionJobStatus.QUEUED):
    mission = CompanyMission(name=name, objective=f"Recover {name}")
    plan = build_mission_plan(mission)
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=status,
        message="persisted",
        attempts=3,
    )


def make_factory(job_store, store=None):
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

def test_restore_recovers_queued_durable_job_without_project_snapshot():
    job = make_job("Orphan queued job")
    factory = make_factory(JobStore([job]))

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    project = factory.queue[0]
    assert project.mission.id == job.id
    assert project.status == "queued"
    assert project.attempts == 3

def test_restore_recovers_running_orphan_and_persists_queued_lifecycle():
    job = make_job("Orphan running job", MissionJobStatus.RUNNING)
    job.plan.steps[0].status = "running"
    store = JobStore([job])
    factory = make_factory(store)

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    assert factory.queue[0].plan.steps[0].status == "planned"
    assert store.jobs[job.id].status == MissionJobStatus.QUEUED
    assert store.jobs[job.id].plan.steps[0].status == "planned"

def test_restore_skips_terminal_orphans_and_uses_jobs_when_project_store_is_down():
    completed = make_job("Completed orphan", MissionJobStatus.COMPLETED)
    queued = make_job("Queued orphan")
    store = JobStore([completed, queued])
    factory = make_factory(store, BrokenProjectStore())

    assert factory.restore() == 1
    assert [project.mission.id for project in factory.queue] == [queued.id]

def test_restore_is_idempotent_for_durable_orphans():
    job = make_job("Idempotent orphan")
    factory = make_factory(JobStore([job]))

    assert factory.restore() == 1
    assert factory.restore() == 0
    assert len(factory.queue) == 1

def test_restore_skips_orphaned_job_with_mismatched_identity():
    job = make_job("Mismatched identity")
    corrupt_job = job.model_copy(update={"id": "different-mission-id"})
    factory = make_factory(JobStore([corrupt_job]))

    assert factory.restore() == 0
    assert factory.queue == []

def test_restore_skips_orphaned_job_with_unknown_lifecycle_status():
    job = make_job("Unknown lifecycle")
    corrupt_job = job.model_copy(update={"status": "waiting_for_magic"})
    factory = make_factory(JobStore([corrupt_job]))

    assert factory.restore() == 0
    assert factory.queue == []

def test_restore_does_not_resurrect_snapshot_when_durable_job_identity_mismatches():
    job = make_job("Snapshot identity mismatch")
    corrupt_job = job.model_copy(update={"id": "different-mission-id"})
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": 0,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(JobStore([corrupt_job]), SnapshotStore())

    assert factory.restore() == 0
    assert factory.queue == []

def test_restore_does_not_resurrect_snapshot_with_unknown_durable_status():
    job = make_job("Snapshot unknown status")
    corrupt_job = job.model_copy(update={"status": "waiting_for_magic"})
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": 0,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(JobStore([corrupt_job]), SnapshotStore())

    assert factory.restore() == 0
    assert factory.queue == []

def test_restore_skips_terminal_snapshot_without_durable_job():
    job = make_job("Terminal snapshot without durable job")
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "completed",
        "attempts": 0,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(None, SnapshotStore())

    assert factory.restore() == 0
    assert factory.queue == []

def test_restore_skips_snapshot_with_unknown_lifecycle_without_durable_job():
    job = make_job("Unknown snapshot lifecycle")
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "waiting_for_magic",
        "attempts": 0,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(None, SnapshotStore())

    assert factory.restore() == 0
    assert factory.queue == []

def test_restore_uses_queued_durable_lifecycle_over_stale_snapshot_status():
    job = make_job("Durable queued lifecycle wins")
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "completed",
        "attempts": 0,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(JobStore([job]), SnapshotStore())

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    assert factory.queue[0].status == "queued"

def test_restore_malformed_duplicate_snapshot_does_not_shadow_valid_snapshot():
    job = make_job("Valid snapshot after malformed duplicate")
    malformed_snapshot = {
        "mission": job.mission,
        "plan": None,
        "status": "queued",
        "attempts": 0,
    }
    valid_snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": 2,
    }

    class SnapshotStore:
        def load_pending(self):
            return [malformed_snapshot, valid_snapshot]

        def save(self, _project):
            pass

    factory = make_factory(None, SnapshotStore())

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    assert factory.queue[0].mission.id == job.id
    assert factory.queue[0].attempts == 2

def test_restore_bounds_untrusted_snapshot_counters():
    job = make_job("Snapshot with oversized counters")
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": 10**100,
        "stages_executed": 10**100,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(None, SnapshotStore())

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    assert factory.queue[0].attempts == 1_000_000
    assert factory.queue[0].stages_executed == 1_000_000


def test_restore_normalizes_non_finite_snapshot_counters():
    job = make_job("Snapshot with non-finite counters")
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": float("inf"),
        "stages_executed": float("nan"),
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(None, SnapshotStore())

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    assert factory.queue[0].attempts == 0
    assert factory.queue[0].stages_executed == 0


def test_mission_job_model_bounds_untrusted_attempts():
    job = make_job("Bounded durable attempts").model_copy(update={"attempts": 10**100})
    # Recovery must defend against model_copy and legacy deserialization bypasses.
    factory = make_factory(JobStore([job]))

    assert factory.restore() == 1
    assert factory.queue[0].attempts == MAX_MISSION_ATTEMPTS


def test_mission_job_validation_caps_attempts_and_normalizes_non_finite_values():
    job = make_job("Validated durable attempts")
    oversized = MissionJob.model_validate({**job.model_dump(), "attempts": 10**100})
    non_finite = MissionJob.model_validate({**job.model_dump(), "attempts": float("inf")})

    assert oversized.attempts == MAX_MISSION_ATTEMPTS
    assert non_finite.attempts == 0


def test_restore_persists_normalized_attempts_for_queued_orphan_job():
    job = make_job("Persist normalized orphan attempts")
    corrupt_job = job.model_copy(update={"attempts": 10**100})
    store = JobStore([corrupt_job])
    factory = make_factory(store)

    assert factory.restore() == 1
    assert factory.queue[0].attempts == MAX_MISSION_ATTEMPTS
    assert store.jobs[job.id].attempts == MAX_MISSION_ATTEMPTS


def test_restore_persists_normalized_attempts_for_snapshot_backed_job():
    job = make_job("Persist normalized snapshot-backed attempts")
    corrupt_job = job.model_copy(update={"attempts": float("inf")})
    store = JobStore([corrupt_job])
    snapshot = {
        "mission": job.mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": 2,
    }

    class SnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            pass

    factory = make_factory(store, SnapshotStore())

    assert factory.restore() == 1
    assert factory.queue[0].attempts == 2
    assert store.jobs[job.id].attempts == 0



def test_restore_persists_sanitized_mission_for_queued_orphan_job():
    job = make_job("Persist sanitized orphan mission")
    unsafe_mission = job.mission.model_copy(
        update={"objective": "Build safely with token=sk-proj-123456789012"}
    )
    corrupt_job = job.model_copy(update={"mission": unsafe_mission})
    store = JobStore([corrupt_job])
    factory = make_factory(store)

    assert factory.restore() == 1
    persisted_objective = store.jobs[job.id].mission.objective
    assert "sk-proj-123456789012" not in persisted_objective
    assert "[REDACTED_TOKEN]" in persisted_objective


def test_restore_skips_queued_orphan_when_sanitized_state_cannot_be_saved():
    job = make_job("Do not queue unsaved sanitized orphan")
    unsafe_mission = job.mission.model_copy(
        update={"objective": "Build safely with token=sk-proj-123456789012"}
    )
    corrupt_job = job.model_copy(update={"mission": unsafe_mission})

    class BrokenJobStore(JobStore):
        def save(self, _job):
            raise OSError("durable job store unavailable")

    factory = make_factory(BrokenJobStore([corrupt_job]))

    assert factory.restore() == 0
    assert factory.queue == []


def test_restore_fails_closed_when_sanitized_snapshot_cannot_be_persisted():
    job = make_job("Unsafe legacy snapshot")
    unsafe_mission = job.mission.model_copy(
        update={"objective": "Build safely with token=sk-proj-123456789012"}
    )
    snapshot = {
        "mission": unsafe_mission,
        "plan": job.plan,
        "status": "queued",
        "attempts": 10**100,
        "stages_executed": 0,
    }

    class BrokenSnapshotStore:
        def load_pending(self):
            return [snapshot]

        def save(self, _project):
            raise OSError("snapshot store is read-only")

    factory = make_factory(None, BrokenSnapshotStore())

    assert factory.restore() == 0
    assert factory.queue == []
