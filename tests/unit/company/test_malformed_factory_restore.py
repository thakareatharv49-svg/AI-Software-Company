from runtime.models.messages import ModelResponse

from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        return ModelResponse(content="stage completed", model="fake", provider="fake")


def test_restore_skips_malformed_snapshot_and_recovers_later_valid_mission():
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    valid_mission = CompanyMission(name="Recoverable", objective="Restore valid work")
    valid_snapshot = {
        "mission": valid_mission,
        "plan": build_mission_plan(valid_mission),
        "status": "queued",
        "stages_executed": 2,
        "attempts": 0,
    }

    class Store:
        def load_pending(self):
            return [
                {"mission": None, "plan": None, "status": "queued"},
                valid_snapshot,
            ]

        def save(self, project):
            pass

    factory = ProjectFactory(orchestrator, controller, pipeline, store=Store())

    assert factory.restore() == 1
    assert len(factory.queue) == 1
    assert factory.queue[0].mission.id == valid_mission.id
    assert factory.queue[0].stages_executed == 2

def test_restore_skips_snapshot_with_malformed_nested_mission_and_continues():
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    malformed_mission = CompanyMission(
        name="Malformed", objective="Invalid legacy payload"
    ).model_copy(update={"constraints": None})
    valid_mission = CompanyMission(
        name="Still recoverable", objective="Restore valid work"
    )
    snapshots = [
        {
            "mission": malformed_mission,
            "plan": build_mission_plan(CompanyMission(
                name="Malformed", objective="Invalid legacy payload"
            )),
            "status": "queued",
            "stages_executed": 0,
            "attempts": 0,
        },
        {
            "mission": valid_mission,
            "plan": build_mission_plan(valid_mission),
            "status": "queued",
            "stages_executed": 1,
            "attempts": 0,
        },
    ]

    class Store:
        def load_pending(self):
            return snapshots

        def save(self, project):
            pass

    factory = ProjectFactory(orchestrator, controller, pipeline, store=Store())

    assert factory.restore() == 1
    assert [project.mission.id for project in factory.queue] == [valid_mission.id]

def test_restore_normalizes_legacy_snapshot_counters():
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    mission = CompanyMission(name="Legacy counters", objective="Recover safely")
    snapshot = {
        "mission": mission,
        "plan": build_mission_plan(mission),
        "status": "queued",
        "stages_executed": -5,
        "attempts": "not-a-number",
    }

    class Store:
        def load_pending(self):
            return [snapshot]

        def save(self, project):
            pass

    factory = ProjectFactory(orchestrator, controller, pipeline, store=Store())

    assert factory.restore() == 1
    assert factory.queue[0].attempts == 0
    assert factory.queue[0].stages_executed == 0

