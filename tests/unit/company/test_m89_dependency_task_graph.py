from src.company.mission_controller.models import EngineeringTask, MissionPlan, MissionStage, PlannedStep
from src.company.mission_controller.planner import validate_mission_plan


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
        "feature", "independent"
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


def test_invalid_task_graph_is_blocked_before_agent_execution():
    mission_plan = plan([task("feature", ["missing"])])
    issues = validate_mission_plan(mission_plan)

    assert issues
    assert any("unknown task" in issue for issue in issues)
