import pytest

from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission, AgentStatus
from src.agents.registry.registry import AgentRegistry
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission, TaskPlanItem
from src.manager.models.enums import ManagerDecisionType, ManagerStatus


def make_agent(name: str = "developer") -> AgentDefinition:
    return AgentDefinition(
        name=name,
        role="software engineer",
        capabilities=["coding"],
        tools=[],
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.WRITE_FILES,
            AgentPermission.RUN_COMMANDS,
            AgentPermission.RUN_TESTS,
        },
        status=AgentStatus.AVAILABLE,
    )


def test_manager_creates_ordered_plan() -> None:
    manager = MasterManager()
    manager.start_mission(
        Mission(
            name="Build product",
            objective="Create a working product",
            project_id="project-1",
        )
    )

    ids = manager.create_plan(
        [
            TaskPlanItem(title="Research"),
            TaskPlanItem(title="Implement", dependencies=(0,)),
        ]
    )

    first = manager.task_engine.get(ids[0])
    second = manager.task_engine.get(ids[1])

    assert first.status.value == "ready"
    assert second.status.value == "blocked"
    assert second.dependencies == [first.id]


@pytest.mark.asyncio
async def test_manager_waits_when_no_agent_is_available() -> None:
    manager = MasterManager()

    manager.start_mission(
        Mission(
            name="Build",
            objective="Build software",
            project_id="project-1",
        )
    )
    ids = manager.create_plan([TaskPlanItem(title="Implement")])

    decision = await manager.tick()

    assert decision.decision == ManagerDecisionType.WAIT
    assert decision.task_id is None
    assert ids[0]
    assert manager.status == ManagerStatus.BLOCKED


@pytest.mark.asyncio
async def test_manager_delegates_execution() -> None:
    registry = AgentRegistry()
    registry.register(make_agent())

    async def execute(request):
        class Result:
            success = True
            error = None

        return Result()

    manager = MasterManager(
        agent_registry=registry,
        agent_executor=execute,
    )

    manager.start_mission(
        Mission(
            name="Build",
            objective="Build software",
            project_id="project-1",
        )
    )

    ids = manager.create_plan(
        [TaskPlanItem(title="Implement", description="Implement feature")]
    )

    decision = await manager.tick()

    assert decision.decision == ManagerDecisionType.START_TASK
    assert decision.task_id == ids[0]
    assert manager.task_engine.get(ids[0]).status.value == "completed"


@pytest.mark.asyncio
async def test_manager_blocks_when_execution_fails() -> None:
    registry = AgentRegistry()
    registry.register(make_agent())

    async def execute(request):
        class Result:
            success = False
            error = "Tests failed"

        return Result()

    manager = MasterManager(
        agent_registry=registry,
        agent_executor=execute,
    )

    manager.start_mission(
        Mission(
            name="Build",
            objective="Build software",
            project_id="project-1",
        )
    )
    ids = manager.create_plan([TaskPlanItem(title="Test")])

    decision = await manager.tick()

    assert decision.decision == ManagerDecisionType.WAIT
    assert manager.task_engine.get(ids[0]).status.value == "failed"
    assert manager.status == ManagerStatus.IDLE
