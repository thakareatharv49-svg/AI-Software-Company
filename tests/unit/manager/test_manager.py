import asyncio

import pytest

from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission, AgentStatus
from src.agents.registry.registry import AgentRegistry
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission, TaskPlanItem
from src.manager.models.enums import ManagerDecisionType, ManagerStatus


def make_agent(name: str = "developer", capacity: int = 1) -> AgentDefinition:
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
        max_concurrent_tasks=capacity,
    )


def make_mission() -> Mission:
    return Mission(name="Build", objective="Build software", project_id="project-1")


def test_manager_creates_ordered_plan() -> None:
    manager = MasterManager()
    manager.start_mission(
        Mission(name="Build product", objective="Create a working product", project_id="project-1")
    )
    ids = manager.create_plan([
        TaskPlanItem(title="Research"),
        TaskPlanItem(title="Implement", dependencies=(0,)),
    ])
    first = manager.task_engine.get(ids[0])
    second = manager.task_engine.get(ids[1])
    assert first.status.value == "ready"
    assert second.status.value == "blocked"
    assert second.dependencies == [first.id]


@pytest.mark.parametrize(
    "items",
    [
        [TaskPlanItem(title="Task", dependencies=(-1,))],
        [TaskPlanItem(title="Task", dependencies=(0,))],
        [
            TaskPlanItem(title="First"),
            TaskPlanItem(title="Second", dependencies=(1,)),
        ],
        [
            TaskPlanItem(title="First"),
            TaskPlanItem(title="Second", dependencies=(0, 0)),
        ],
        [
            TaskPlanItem(title="First"),
            TaskPlanItem(title="Second", dependencies=("0",)),
        ],
    ],
)
def test_manager_rejects_invalid_dependency_graph_before_creating_tasks(items) -> None:
    manager = MasterManager()
    manager.start_mission(make_mission())

    with pytest.raises(ValueError, match="dependency"):
        manager.create_plan(items)

    assert manager.task_engine.list(project_id="project-1") == []


@pytest.mark.asyncio
def test_manager_delegates_execution() -> None:
    registry = AgentRegistry()
    registry.register(make_agent())

    async def execute(request):
        class Result:
            success = True
            error = None
        return Result()

    manager = MasterManager(agent_registry=registry, agent_executor=execute)
    manager.start_mission(make_mission())
    ids = manager.create_plan([TaskPlanItem(title="Implement", description="Implement feature")])
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

    manager = MasterManager(agent_registry=registry, agent_executor=execute)
    manager.start_mission(make_mission())
    ids = manager.create_plan([TaskPlanItem(title="Test")])
    decision = await manager.tick()
    assert decision.decision == ManagerDecisionType.WAIT
    assert manager.task_engine.get(ids[0]).status.value == "failed"
    assert manager.status == ManagerStatus.IDLE


@pytest.mark.asyncio
async def test_parallel_tick_executes_independent_tasks_concurrently() -> None:
    registry = AgentRegistry()
    registry.register(make_agent(capacity=2))
    manager = MasterManager(agent_registry=registry)
    manager.start_mission(make_mission())
    ids = manager.create_plan([
        TaskPlanItem(title="Frontend"),
        TaskPlanItem(title="Backend"),
        TaskPlanItem(title="QA", dependencies=(0, 1)),
    ])
    active = 0
    max_active = 0

    async def execute(request):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.02)
        active -= 1

        class Result:
            success = True
            error = None
        return Result()

    decision = await manager.tick_parallel(executor=execute, max_concurrency=2)
    assert decision.decision == ManagerDecisionType.START_TASK
    assert max_active == 2
    assert all(manager.task_engine.get(task_id).status.value == "completed" for task_id in ids[:2])
    assert manager.task_engine.get(ids[2]).status.value == "blocked"
    next_decision = await manager.tick_parallel(executor=execute, max_concurrency=2)
    assert next_decision.decision == ManagerDecisionType.START_TASK
    assert manager.task_engine.get(ids[2]).status.value == "completed"


@pytest.mark.asyncio
async def test_parallel_tick_respects_agent_capacity_and_reports_failure() -> None:
    registry = AgentRegistry()
    registry.register(make_agent(capacity=1))
    manager = MasterManager(agent_registry=registry)
    manager.start_mission(make_mission())
    ids = manager.create_plan([TaskPlanItem(title="One"), TaskPlanItem(title="Two")])

    async def fail(request):
        class Result:
            success = False
            error = "subsystem failed"
        return Result()

    decision = await manager.tick_parallel(executor=fail, max_concurrency=2)
    assert decision.decision == ManagerDecisionType.WAIT
    assert decision.reason == "subsystem failed"
    assert manager.task_engine.get(ids[0]).status.value == "failed"
    assert manager.task_engine.get(ids[1]).status.value == "ready"
