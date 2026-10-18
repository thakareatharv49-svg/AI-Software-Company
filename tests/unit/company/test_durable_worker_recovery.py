from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class _Runtime:
    async def generate(self, request):
        return ModelResponse(content="ok", model="test", provider="test")


class _ChangingJobStore:
    def __init__(self):
        self.jobs = {}
        self.list_calls = 0

    def get(self, job_id):
        return self.jobs.get(job_id)

    def save(self, job):
        self.jobs[job.id] = job

    def list_all(self):
        self.list_calls += 1
        if self.list_calls == 1:
            return list(self.jobs.values())
        # Simulate a changing view that would not have passed the first
        # identity validation if it had been used for recovery.
        return []


def _factory(job_store):
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator, AgentExecutor(_Runtime()), AgentRegistry()
    )
    return ProjectFactory(orchestrator, controller, pipeline, job_store=job_store)


def test_restore_reuses_validated_job_enumeration_for_orphan_recovery():
    store = _ChangingJobStore()
    factory = _factory(store)
    mission = CompanyMission(name="Recover after restart", objective="Do not lose queued work")
    factory.enqueue(mission)
    factory.queue.clear()  # Simulate a process restart with no in-memory queue.
    store.list_calls = 0

    restored = factory.restore()

    assert restored == 1
    assert store.list_calls == 1
    assert [project.mission.id for project in factory.queue] == [mission.id]