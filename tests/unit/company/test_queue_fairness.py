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


def test_retry_requeue_moves_mission_behind_waiting_work_and_removes_duplicates():
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator, AgentExecutor(_Runtime()), AgentRegistry()
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)
    retrying = factory.enqueue(
        CompanyMission(name="Retrying", objective="Must yield to waiting work")
    )
    waiting_a = factory.enqueue(
        CompanyMission(name="Waiting A", objective="Already waiting")
    )
    waiting_b = factory.enqueue(
        CompanyMission(name="Waiting B", objective="Also waiting")
    )
    # Model a stale queue entry left by an interrupted cleanup/recovery path.
    factory.queue = [retrying, waiting_a, retrying, waiting_b]

    factory._requeue_for_fairness(retrying)

    assert [item.mission.id for item in factory.queue] == [
        waiting_a.mission.id,
        waiting_b.mission.id,
        retrying.mission.id,
    ]
    assert len({item.mission.id for item in factory.queue}) == len(factory.queue)