from src.company.models.contracts import CompanyMission
from src.company.models.enums import CompanyDecision, CompanyStatus
from src.company.orchestration.orchestrator import CompanyOrchestrator


def create_mission() -> CompanyMission:
    return CompanyMission(
        name="Build useful developer software",
        objective="Continuously create meaningful open-source software",
    )


def test_company_starts_with_mission() -> None:
    company = CompanyOrchestrator()

    result = company.start(create_mission())

    assert result.decision == CompanyDecision.CONTINUE
    assert result.state.status == CompanyStatus.RUNNING


def test_company_can_select_project_and_task() -> None:
    company = CompanyOrchestrator()

    company.start(create_mission())

    project = company.assign_project("project-1")
    task = company.assign_task("task-1")

    assert project.state.current_project_id == "project-1"
    assert task.state.current_task_id == "task-1"


def test_completed_task_clears_active_task() -> None:
    company = CompanyOrchestrator()

    company.start(create_mission())
    company.assign_project("project-1")
    company.assign_task("task-1")

    result = company.complete_task()

    assert result.decision == CompanyDecision.CONTINUE
    assert result.state.current_task_id is None
    assert result.state.completed_tasks == 1


def test_completed_project_allows_next_project() -> None:
    company = CompanyOrchestrator()

    company.start(create_mission())
    company.assign_project("project-1")
    company.assign_task("task-1")
    company.complete_task()

    result = company.complete_project()

    assert result.decision == CompanyDecision.COMPLETE_PROJECT
    assert result.state.current_project_id is None
    assert result.state.completed_projects == 1


def test_task_requires_project() -> None:
    company = CompanyOrchestrator()

    company.start(create_mission())

    result = company.assign_task("task-1")

    assert result.decision == CompanyDecision.BLOCK


def test_blocked_company_records_event() -> None:
    company = CompanyOrchestrator()

    company.start(create_mission())

    result = company.block("Security gate failed")

    assert result.decision == CompanyDecision.BLOCK
    assert result.state.status == CompanyStatus.BLOCKED
    assert len(company.events.list_events()) == 2
    assert company.events.list_events()[-1].event_type == "COMPANY_BLOCKED"


def test_stopping_company_records_event() -> None:
    company = CompanyOrchestrator()

    company.start(create_mission())

    result = company.stop()

    assert result.decision == CompanyDecision.STOP
    assert result.state.status == CompanyStatus.STOPPED
    assert company.events.list_events()[-1].event_type == "COMPANY_STOPPED"
