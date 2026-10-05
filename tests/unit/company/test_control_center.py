from fastapi.testclient import TestClient

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter, MissionSubmission
from src.company.models.contracts import CompanyState
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.main import app


def test_submit_mission_starts_company() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    record = center.submit_mission(
        MissionSubmission(name="Build X", objective="Create X for users")
    )
    assert record.status == "running"
    assert record.mission.objective == "Create X for users"
    assert center.state.status.value == "running"


def test_running_company_rejects_second_mission() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    center.submit_mission(MissionSubmission(name="First", objective="First objective"))
    try:
        center.submit_mission(MissionSubmission(name="Second", objective="Second objective"))
    except RuntimeError as exc:
        assert "already running" in str(exc)
    else:
        raise AssertionError("expected running-company guard")


def test_control_api_serves_mission_and_app() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post("/api/missions", json={"name": "Build X", "objective": "Create X"})
        assert response.status_code == 201
        assert response.json()["status"] == "running"
        assert client.get("/api/company/state").json()["status"] == "running"
        assert client.get("/app").status_code == 200
        assert "AI Software Company" in client.get("/app").text
    finally:
        app.dependency_overrides.clear()


def test_stop_control_changes_company_state() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    center.submit_mission(MissionSubmission(name="Build X", objective="Create X"))
    state = center.stop()
    assert isinstance(state, CompanyState)
    assert state.status.value == "stopped"
