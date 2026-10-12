from src.company.mission_controller.planner import build_mission_plan, validate_mission_plan
from src.company.models.contracts import CompanyMission


def make_plan():
    return build_mission_plan(
        CompanyMission(name="Plan validation", objective="Build a useful application with tests.")
    )


def test_generated_mission_plan_has_valid_dependencies():
    assert validate_mission_plan(make_plan()) == []


def test_validation_reports_unknown_task_and_stage_dependencies():
    plan = make_plan()
    plan.engineering_tasks[0].depends_on = ["missing-task"]
    plan.steps[0].depends_on = ["missing-stage"]

    issues = validate_mission_plan(plan)

    assert any("unknown task 'missing-task'" in issue for issue in issues)
    assert any("unknown stage 'missing-stage'" in issue for issue in issues)


def test_validation_reports_dependency_cycles():
    plan = make_plan()
    first, second = plan.engineering_tasks[:2]
    first.depends_on = [second.id]
    second.depends_on = [first.id]
    plan.steps[0].depends_on = [plan.steps[-1].stage.value]
    plan.steps[-1].depends_on = [plan.steps[0].stage.value]

    issues = validate_mission_plan(plan)

    assert any("Engineering task dependency graph contains a cycle" in issue for issue in issues)
    assert any("Lifecycle stage dependency graph contains a cycle" in issue for issue in issues)


def test_validation_requires_acceptance_criteria_and_engineering_tasks():
    plan = make_plan()
    plan.acceptance_criteria = []
    plan.engineering_tasks = []

    issues = validate_mission_plan(plan)

    assert "Mission plan must contain at least one acceptance criterion." in issues
    assert "Mission plan must contain at least one engineering task." in issues
