from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.persistence import _safe_factory_snapshot
from src.company.project_factory import FactoryProject


def test_factory_snapshot_is_redacted_and_bounded_before_write() -> None:
    mission = CompanyMission(
        name="Factory snapshot",
        objective="token=samplevalue123456 " + ("o" * 9000),
        constraints=["c" * 3000],
    )
    plan = build_mission_plan(mission)
    plan.steps[0].detail = "d" * 6000
    project = FactoryProject(
        mission=mission,
        plan=plan,
        status="queued" + ("s" * 100),
        stages_executed=-2,
        attempts=-3,
    )

    safe = _safe_factory_snapshot(project)

    assert "samplevalue123456" not in safe["mission"]["objective"]
    assert len(safe["mission"]["objective"]) == 8000
    assert len(safe["mission"]["constraints"][0]) == 2000
    assert len(safe["plan"]["steps"][0]["detail"]) == 4000
    assert len(safe["status"]) <= 32
    assert safe["stages_executed"] == 0
    assert safe["attempts"] == 0
