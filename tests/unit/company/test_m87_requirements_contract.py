from src.company.mission_controller.models import MissionPlan
from src.company.mission_controller.planner import (
    build_mission_plan,
    build_requirements_contract,
    validate_mission_plan,
)
from src.company.models.contracts import CompanyMission


def test_contract_is_deterministic_and_traces_objective_constraints():
    mission = CompanyMission(
        id="mission-123",
        name="Expense tracker",
        objective="Build a responsive expense tracker. Support create, edit, and delete transactions.",
        constraints=["Use local persistence", "Use local persistence"],
    )

    first = build_requirements_contract(mission)
    second = build_requirements_contract(mission)

    assert first.model_dump() == second.model_dump()
    assert first.schema_version == 1
    assert first.status == "ready"
    assert first.mission_id == mission.id
    assert [item.id for item in first.functional_requirements] == ["REQ-001", "REQ-002"]
    assert first.functional_requirements[1].source == "objective"
    assert first.constraints == ["Use local persistence"]
    assert "Constraint: Use local persistence" in first.acceptance_criteria
    assert all(item.acceptance_check for item in first.functional_requirements)


def test_mission_plan_persists_contract_and_generates_traceable_tasks():
    mission = CompanyMission(
        id="mission-plan",
        name="Inventory API",
        objective="Build an inventory API with create, read, update, and delete endpoints.",
        constraints=["Include automated tests"],
    )

    plan = build_mission_plan(mission)

    assert plan.requirements_contract is not None
    assert plan.requirements_contract.mission_id == plan.mission_id
    assert plan.acceptance_criteria == plan.requirements_contract.acceptance_criteria
    assert len(plan.engineering_tasks) == len(plan.acceptance_criteria) * 3
    assert validate_mission_plan(plan) == []


def test_generic_mission_is_flagged_for_clarification_before_implementation():
    mission = CompanyMission(name="App", objective="Build an app")

    contract = build_requirements_contract(mission)
    plan = build_mission_plan(mission)

    assert contract.status == "needs_clarification"
    assert contract.open_questions
    assert any("Specify the target users" in issue for issue in validate_mission_plan(plan))


def test_contract_plan_mismatch_is_reported():
    plan = build_mission_plan(
        CompanyMission(
            id="mission-original",
            name="Notes",
            objective="Build a notes app with searchable notes and persistent storage.",
        )
    )
    assert plan.requirements_contract is not None
    plan.requirements_contract.mission_id = "different-mission"

    assert "Requirements contract mission ID does not match its plan." in validate_mission_plan(plan)


def test_legacy_persisted_plan_without_contract_remains_loadable():
    plan = build_mission_plan(
        CompanyMission(
            id="mission-legacy-source",
            name="CLI utility",
            objective="Build a CLI utility with add and list commands.",
        )
    )
    payload = plan.model_dump()
    payload.pop("requirements_contract")
    restored = MissionPlan.model_validate(payload)

    assert restored.requirements_contract is None
    assert restored.mission_id == plan.mission_id
