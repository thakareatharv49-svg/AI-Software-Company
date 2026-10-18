import pytest

from src.company.mission_controller.models import (
    EngineeringTask,
    MissionPlan,
    MissionStage,
    PlannedStep,
)


def task(task_id: str, dependencies: list[str] | None = None, status: str = "planned") -> EngineeringTask:
    return EngineeringTask(
        id=task_id,
        title=task_id,
        requirement=f"Requirement for {task_id}",
        workstream="product",
        depends_on=dependencies or [],
        agent_role="generalist",
        acceptance_check=f"Check {task_id}",
        status=status,
    )


def plan(*tasks: EngineeringTask) -> MissionPlan:
    return MissionPlan(
        mission_id="mission-1",
        name="Multi-feature fixture",
        objective="Exercise dependency scheduling",
        engineering_tasks=list(tasks),
        steps=[PlannedStep(stage=MissionStage.TASKS, objective="Plan tasks")],
    )


def test_task_order_is_dependency_first_and_stable_for_independent_slices() -> None:
    value = plan(task("frontend", ["api"]), task("docs"), task("api"))

    assert [item.id for item in value.engineering_task_order()] == ["docs", "api", "frontend"]


def test_only_planned_tasks_with_completed_prerequisites_are_ready() -> None:
    value = plan(task("api", status="completed"), task("frontend", ["api"]), task("deploy", ["frontend"]))

    assert [item.id for item in value.ready_engineering_tasks()] == ["frontend"]
    value.engineering_tasks[1].status = "completed"
    assert [item.id for item in value.ready_engineering_tasks()] == ["deploy"]


def test_missing_dependency_is_rejected_with_actionable_error() -> None:
    value = plan(task("frontend", ["missing-api"]))

    with pytest.raises(ValueError, match="missing dependencies: missing-api"):
        value.engineering_task_order()


def test_dependency_cycle_is_rejected() -> None:
    value = plan(task("api", ["frontend"]), task("frontend", ["api"]))

    with pytest.raises(ValueError, match="contain a cycle"):
        value.engineering_task_order()


def test_duplicate_task_ids_are_rejected() -> None:
    value = plan(task("api"), task("api"))

    with pytest.raises(ValueError, match="unique non-empty"):
        value.engineering_task_order()
