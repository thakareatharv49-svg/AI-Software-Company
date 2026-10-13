from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.persistence import _safe_mission, _safe_plan


def test_persisted_mission_text_is_bounded_before_use() -> None:
    mission = CompanyMission(name="n" * 900, objective="o" * 12000, constraints=["c" * 3000])
    safe = _safe_mission(mission)

    assert len(safe.name) == 500
    assert len(safe.objective) == 8000
    assert len(safe.constraints[0]) == 2000


def test_persisted_plan_text_is_bounded_without_losing_progress() -> None:
    mission = CompanyMission(name="Restore", objective="Restore a plan safely")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "d" * 6000
    plan.engineering_tasks[0].requirement = "r" * 6000

    safe = _safe_plan(plan)

    assert safe.steps[0].status == "completed"
    assert len(safe.steps[0].detail) == 4000
    assert len(safe.engineering_tasks[0].requirement) == 4000
