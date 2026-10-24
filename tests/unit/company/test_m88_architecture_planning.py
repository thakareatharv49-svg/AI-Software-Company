from src.company.mission_controller.architecture import build_architecture_plan
from src.company.mission_controller.models import MissionPlan, RuntimeCapabilities
from src.company.mission_controller.planner import build_mission_plan, validate_mission_plan
from src.company.models.contracts import CompanyMission


def mission(objective: str) -> CompanyMission:
    return CompanyMission(id="m88-mission", name="Architecture fixture", objective=objective)


def test_browser_mission_selects_browser_stack_and_reviewable_layout():
    plan = build_mission_plan(
        mission("Build a responsive browser app dashboard with persistent settings.")
    )

    architecture = plan.architecture_plan
    assert architecture is not None
    assert architecture.project_type == "browser_app"
    assert architecture.language == "javascript"
    assert "index.html" in architecture.repository_layout
    assert any("Browser interaction" in item for item in architecture.validation_strategy)
    assert architecture.status == "ready"
    assert validate_mission_plan(plan) == []


def test_api_mission_selects_api_stack_and_interfaces():
    architecture = build_architecture_plan(mission("Build a REST API with CRUD endpoints."))

    assert architecture.project_type == "api_service"
    assert architecture.framework == "fastapi"
    assert "HTTP API contract" in architecture.interfaces
    assert "src/routes/" in architecture.repository_layout
    assert architecture.dependencies
    assert architecture.status == "ready"


def test_cli_mission_does_not_default_to_a_web_demo():
    architecture = build_architecture_plan(mission("Build a CLI utility with add and list commands."))

    assert architecture.project_type == "cli_utility"
    assert "src/cli.py" in architecture.repository_layout
    assert "index.html" not in architecture.repository_layout
    assert "Stable exit codes" in architecture.interfaces


def test_missing_required_runtime_capability_blocks_architecture_before_coding():
    architecture = build_architecture_plan(
        mission("Build a REST API with CRUD endpoints."),
        capabilities=RuntimeCapabilities(
            languages=["python"],
            frameworks=[],
            tools=["python"],
            packages=[],
            database_engines=[],
        ),
    )

    assert architecture.status == "blocked_unsupported_dependency"
    assert "pytest" in architecture.unsupported_dependencies
    assert any(not item.available for item in architecture.dependencies)


def test_architecture_plan_is_persisted_and_validation_checks_its_identity():
    plan = build_mission_plan(
        mission("Build a responsive browser app with searchable notes.")
    )

    assert plan.architecture_plan is not None
    assert plan.architecture_plan.mission_id == plan.mission_id
    payload = plan.model_dump()
    restored = MissionPlan.model_validate(payload)
    assert restored.architecture_plan is not None
    assert restored.architecture_plan.project_type == "browser_app"

    restored.architecture_plan.mission_id = "different-mission"
    assert "Architecture plan mission ID does not match its plan." in validate_mission_plan(restored)


def test_legacy_plan_without_architecture_remains_loadable():
    plan = build_mission_plan(mission("Build a CLI utility with import and export commands."))
    payload = plan.model_dump()
    payload.pop("architecture_plan")
    payload.pop("requirements_contract")
    restored = MissionPlan.model_validate(payload)

    assert restored.architecture_plan is None
    assert restored.requirements_contract is None
