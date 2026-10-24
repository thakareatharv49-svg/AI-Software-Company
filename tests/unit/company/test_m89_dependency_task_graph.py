import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.models import EngineeringTask, MissionPlan, MissionStage, PlannedStep
from src.company.mission_controller.planner import validate_mission_plan
from src.company.mission_jobs import recover_running_plan, resume_failed_plan
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


def task(task_id: str, dependencies: list[str] | None = None, status: str = "planned") -> EngineeringTask:
    return EngineeringTask(
        id=task_id,
        title=task_id,
        requirement=f"Requirement for {task_id}",
        workstream="implementation",
        depends_on=dependencies or [],
        agent_role="software_engineer",
        acceptance_check=f"Verify {task_id}",
        status=status,
    )


def plan(tasks: list[EngineeringTask]) -> MissionPlan:
    return MissionPlan(
        mission_id="m89-fixture",
        name="Dependency graph fixture",
        objective="Exercise dependency-aware scheduling",
        acceptance_criteria=["Task graph has a verified outcome"],
        engineering_tasks=tasks,
        steps=[
            PlannedStep(stage=stage, objective=stage.value)
            for stage in MissionStage
        ],
    )


def test_task_order_is_dependency_first_even_when_input_is_reversed():
    mission_plan = plan([
        task("release", ["test"]),
        task("test", ["build"]),
        task("build"),
    ])

    assert [item.id for item in mission_plan.engineering_task_order()] == [
        "build", "test", "release"
    ]


def test_only_tasks_with_completed_prerequisites_are_ready():
    mission_plan = plan([
        task("foundation", status="completed"),
        task("feature", ["foundation"]),
        task("integration", ["feature"]),
        task("independent"),
    ])

    assert [item.id for item in mission_plan.ready_engineering_tasks()] == [
        "independent", "feature"
    ]


def test_task_graph_rejects_duplicate_ids_and_missing_dependencies():
    duplicate = plan([task("same"), task("same")])
    assert any("unique" in issue for issue in validate_mission_plan(duplicate))

    missing = plan([task("feature", ["unknown"])])
    assert any("unknown task" in issue for issue in validate_mission_plan(missing))


def test_task_graph_rejects_self_dependency_and_cycles():
    self_dependent = plan([task("loop", ["loop"])])
    assert any("cannot depend on itself" in issue for issue in validate_mission_plan(self_dependent))

    cyclic = plan([task("a", ["b"]), task("b", ["a"])])
    assert any("cycle" in issue.lower() for issue in validate_mission_plan(cyclic))
    try:
        cyclic.engineering_task_order()
    except ValueError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("cyclic task graph must not be scheduled")


class FakeProvider:
    name = "fake"

    async def generate(self, request):
        return ModelResponse(
            content=f"completed: {request.prompt[:30]}",
            model="fake",
            provider=self.name,
        )


class FakeRuntime:
    def __init__(self, fail_on_call: int | None = None):
        self.provider = FakeProvider()
        self.calls = 0
        self.fail_on_call = fail_on_call

    async def generate(self, request):
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise RuntimeError("controlled task failure")
        return await self.provider.generate(request)


def execution_fixture(objective: str = "Create a small utility"):
    orchestrator = CompanyOrchestrator()
    mission = CompanyMission(name="M89 task graph", objective=objective)
    controller = MissionController(orchestrator)
    mission_plan, _ = controller.start(mission)
    for step in mission_plan.steps:
        if step.stage in {
            MissionStage.RESEARCH,
            MissionStage.PRODUCT,
            MissionStage.ARCHITECTURE,
            MissionStage.TASKS,
            MissionStage.AGENTS,
        }:
            step.status = "completed"
    runtime = FakeRuntime()
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(runtime),
        AgentRegistry(),
    )
    return mission, mission_plan, orchestrator, runtime, pipeline


@pytest.mark.asyncio
async def test_invalid_task_graph_is_blocked_before_agent_execution():
    mission, mission_plan, orchestrator, runtime, pipeline = execution_fixture()
    mission_plan.engineering_tasks = [task("feature", ["missing"])]

    result = await pipeline.execute_next(mission, mission_plan)

    assert result.success is False
    assert "invalid" in (result.error or "").lower()
    assert runtime.calls == 0
    assert orchestrator.state.status.value == "blocked"


@pytest.mark.asyncio
async def test_execution_stage_runs_each_task_and_checkpoints_every_transition():
    mission, mission_plan, _orchestrator, runtime, pipeline = execution_fixture()
    checkpoints = []

    result = await pipeline.execute_next(
        mission,
        mission_plan,
        on_progress=lambda current: checkpoints.append(
            [(item.id, item.status) for item in current.engineering_tasks]
        ),
    )

    assert result.success is True
    assert runtime.calls == len(mission_plan.engineering_tasks)
    assert all(item.status == "completed" for item in mission_plan.engineering_tasks)
    assert len(checkpoints) >= 2 * len(mission_plan.engineering_tasks)
    assert any(
        any(status == "running" for _, status in snapshot)
        for snapshot in checkpoints
    )
    assert any(
        all(status == "completed" for _, status in snapshot)
        for snapshot in checkpoints
    )


@pytest.mark.asyncio
async def test_failed_task_stops_dependents_and_preserves_checkpointed_prerequisites():
    mission, mission_plan, orchestrator, _runtime, _pipeline = execution_fixture()
    runtime = FakeRuntime(fail_on_call=1)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(runtime),
        AgentRegistry(),
    )
    mission_plan.engineering_tasks = [
        task("foundation"),
        task("feature", ["foundation"]),
        task("release", ["feature"]),
    ]
    checkpoints = []

    result = await pipeline.execute_next(
        mission,
        mission_plan,
        on_progress=lambda current: checkpoints.append(
            [(item.id, item.status) for item in current.engineering_tasks]
        ),
    )

    assert result.success is False
    assert mission_plan.engineering_tasks[0].status == "failed"
    assert mission_plan.engineering_tasks[1].status == "planned"
    assert mission_plan.engineering_tasks[2].status == "planned"
    assert orchestrator.state.status.value == "blocked"
    assert any(
        snapshot[0] == ("foundation", "failed")
        and snapshot[1] == ("feature", "planned")
        for snapshot in checkpoints
    )



def test_restart_requeues_running_task_and_invalidates_completed_descendants():
    mission_plan = plan([
        task("foundation", status="completed"),
        task("feature", ["foundation"], status="running"),
        task("release", ["feature"], status="completed"),
    ])

    recovered = recover_running_plan(mission_plan)

    assert recovered.engineering_tasks[0].status == "completed"
    assert recovered.engineering_tasks[1].status == "planned"
    assert recovered.engineering_tasks[2].status == "planned"
    assert [item.id for item in recovered.ready_engineering_tasks()] == ["feature"]


def test_retry_resets_failed_task_and_completed_descendants_but_keeps_valid_prerequisites():
    mission_plan = plan([
        task("foundation", status="completed"),
        task("feature", ["foundation"], status="failed"),
        task("release", ["feature"], status="completed"),
    ])

    recovered = resume_failed_plan(mission_plan)

    assert recovered.engineering_tasks[0].status == "completed"
    assert recovered.engineering_tasks[1].status == "planned"
    assert recovered.engineering_tasks[2].status == "planned"
    assert [item.id for item in recovered.ready_engineering_tasks()] == ["feature"]



@pytest.mark.asyncio
async def test_real_factory_worker_persists_engineering_task_checkpoints():
    class JobStore:
        def __init__(self):
            self.jobs = {}
            self.history = []

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            snapshot = job.model_copy(deep=True)
            self.jobs[job.id] = snapshot
            self.history.append(snapshot)

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    runtime = FakeRuntime()
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(runtime),
        AgentRegistry(),
    )
    job_store = JobStore()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        job_store=job_store,
    )
    mission = CompanyMission(
        name="Factory task graph acceptance",
        objective="Build a small local utility with a test",
    )
    project = factory.enqueue(mission)

    results = await factory.run(max_projects=1, max_stages=12, max_retries=0)

    assert results == [project]
    assert project.status == "completed"
    assert all(task.status == "completed" for task in project.plan.engineering_tasks)
    persisted_task_states = [
        [task.status for task in snapshot.plan.engineering_tasks]
        for snapshot in job_store.history
    ]
    assert any("running" in statuses for statuses in persisted_task_states)
    assert any(
        statuses and all(status == "completed" for status in statuses)
        for statuses in persisted_task_states
    )
