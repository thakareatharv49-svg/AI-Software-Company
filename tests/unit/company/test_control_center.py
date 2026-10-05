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
    assert [step.stage.value for step in record.plan.steps] == [
        "research", "product", "architecture", "tasks", "agents", "execution",
        "qa", "security", "github", "deployment", "monitoring", "learning",
    ]
    assert center.state.current_project_id == f"project:{record.mission.id}"
    assert center.state.current_task_id == f"task:{record.mission.id}:research"


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


def test_mission_plan_api_exposes_internal_pipeline() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Build X", "objective": "Create X"},
        )
        mission_id = response.json()["mission"]["id"]
        plan = client.get(f"/api/missions/{mission_id}/plan")
        assert plan.status_code == 200
        assert len(plan.json()["steps"]) == 12
        assert plan.json()["steps"][0]["stage"] == "research"
    finally:
        app.dependency_overrides.clear()


def test_mission_job_api_exposes_persistent_lifecycle() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Lifecycle API", "objective": "Expose job state"},
        )
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]

        job = client.get(f"/api/missions/{mission_id}/job")
        assert job.status_code == 200
        assert job.json()["id"] == mission_id
        assert job.json()["status"] == "running"

        jobs = client.get("/api/mission-jobs")
        assert jobs.status_code == 200
        assert any(item["id"] == mission_id for item in jobs.json())
    finally:
        app.dependency_overrides.clear()


def test_mission_cancel_and_retry_api() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post(
            "/api/missions",
            json={"name": "Recovery API", "objective": "Exercise recovery controls"},
        )
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]

        cancelled = client.post(f"/api/missions/{mission_id}/cancel")
        assert cancelled.status_code == 409

        center._job_store.save(
            center.mission_job(mission_id).model_copy(
                update={"status": "blocked", "message": "blocked for retry"}
            )
        )
        retried = client.post(f"/api/missions/{mission_id}/retry")
        assert retried.status_code == 200
        assert retried.json()["status"] == "queued"
    finally:
        app.dependency_overrides.clear()


def test_mission_audit_api_supports_filters() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post("/api/missions", json={"name": "Audit API", "objective": "Inspect lifecycle history"})
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]
        audit = client.get(f"/api/missions/{mission_id}/audit", params={"event_type": "MISSION_CREATED", "status": "running"})
        assert audit.status_code == 200
        assert isinstance(audit.json(), list)
        missing = client.get("/api/missions/missing/audit")
        assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_project_outputs_api() -> None:
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        response = client.post("/api/missions", json={"name": "Outputs API", "objective": "Expose project outputs"})
        assert response.status_code == 201
        mission_id = response.json()["mission"]["id"]
        outputs = client.get(f"/api/missions/{mission_id}/outputs")
        assert outputs.status_code == 200
        assert outputs.json() == []
        assert client.get("/api/missions/missing/outputs").status_code == 404
    finally:
        app.dependency_overrides.clear()
