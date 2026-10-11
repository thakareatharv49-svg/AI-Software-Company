from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry


class MemoryJobStore:
    def __init__(self, job: MissionJob) -> None:
        self.jobs = {job.id: job}

    def get(self, job_id: str) -> MissionJob | None:
        return self.jobs.get(job_id)

    def save(self, job: MissionJob) -> None:
        self.jobs[job.id] = job


class FakeRuntime:
    async def generate(self, request):
        from runtime.models.messages import ModelResponse
        return ModelResponse(content='done', model='fake', provider='fake')


def make_factory(job: MissionJob):
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(orchestrator, AgentExecutor(FakeRuntime()), AgentRegistry())
    store = MemoryJobStore(job)
    factory = ProjectFactory(orchestrator, controller, pipeline, job_store=store)
    return factory, store


def test_revision_requeues_same_mission_with_feedback_and_fresh_plan():
    mission = CompanyMission(name='Task manager', objective='Build task creation and search')
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=MissionJobStatus.COMPLETED,
        message='Project completed',
    )
    factory, store = make_factory(job)

    revised = factory.revise(mission.id, 'Add a calendar view and keep search working')

    assert revised.id == mission.id
    assert revised.status == MissionJobStatus.QUEUED
    assert 'Add a calendar view' in revised.mission.objective
    assert revised.attempts == 0
    assert len(factory.queue) == 1
    assert factory.queue[0].mission.id == mission.id
    assert all(step.status == 'planned' for step in factory.queue[0].plan.steps)
    assert store.get(mission.id).status == MissionJobStatus.QUEUED


def test_revision_rejects_blank_feedback_and_non_completed_jobs():
    mission = CompanyMission(name='Incomplete', objective='Build an app')
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=MissionJobStatus.BLOCKED,
        message='Blocked',
    )
    factory, _ = make_factory(job)
    import pytest
    with pytest.raises(ValueError, match='cannot be revised'):
        factory.revise(mission.id, 'Add search')
    with pytest.raises(KeyError):
        factory.revise('missing-mission', 'Add search')
