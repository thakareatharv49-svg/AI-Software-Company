from fastapi.testclient import TestClient

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.main import app
from src.security.authorization import require_company_owner


def test_mission_lifecycle_acceptance_from_submission_to_safe_cancellation():
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    app.dependency_overrides[require_company_owner] = lambda: None
    try:
        client = TestClient(app)
        created = client.post(
            "/api/missions",
            json={
                "name": "Lifecycle acceptance",
                "objective": "Build a reliable workspace with saved records and automated tests.",
                "constraints": ["Keep generated files local"],
            },
        )
        assert created.status_code == 201
        mission_id = created.json()["mission"]["id"]

        job = client.get(f"/api/missions/{mission_id}/job")
        assert job.status_code == 200
        assert job.json()["status"] == "queued"

        plan = client.get(f"/api/missions/{mission_id}/plan")
        assert plan.status_code == 200
        assert len(plan.json()["acceptance_criteria"]) >= 2
        assert len(plan.json()["engineering_tasks"]) >= 6

        validation = client.get(f"/api/missions/{mission_id}/plan/validation")
        assert validation.status_code == 200
        assert validation.json()["valid"] is True
        assert validation.json()["stage_count"] == 12
        assert validation.json()["engineering_task_count"] >= 6

        diagnostics = client.get(f"/api/missions/{mission_id}/diagnostics")
        assert diagnostics.status_code == 200
        assert diagnostics.json()["mission_id"] == mission_id

        cancelled = client.post(f"/api/missions/{mission_id}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"

        final_job = client.get(f"/api/missions/{mission_id}/job")
        assert final_job.status_code == 200
        assert final_job.json()["status"] == "cancelled"
        final_diagnostics = client.get(f"/api/missions/{mission_id}/diagnostics")
        assert final_diagnostics.status_code == 200
        assert final_diagnostics.json()["diagnosis"] == "cancelled"
    finally:
        app.dependency_overrides.clear()


def test_queued_mission_can_be_deleted_without_touching_other_missions():
    center = CompanyControlCenter(CompanyOrchestrator())
    app.dependency_overrides[get_control_center] = lambda: center
    app.dependency_overrides[require_company_owner] = lambda: None
    try:
        client = TestClient(app)
        first = client.post(
            "/api/missions",
            json={"name": "Delete target", "objective": "Create a disposable queued record"},
        )
        second = client.post(
            "/api/missions",
            json={"name": "Keep target", "objective": "Keep this queued record"},
        )
        assert first.status_code == 201
        assert second.status_code == 201
        first_id = first.json()["mission"]["id"]
        second_id = second.json()["mission"]["id"]

        deleted = client.delete(f"/api/missions/{first_id}")
        assert deleted.status_code == 200
        assert deleted.json() == {"deleted": True, "mission_id": first_id}
        assert client.get(f"/api/missions/{first_id}/job").status_code == 404
        kept_job = client.get(f"/api/missions/{second_id}/job")
        assert kept_job.status_code == 200
        assert kept_job.json()["id"] == second_id
        assert kept_job.json()["status"] == "queued"
    finally:
        app.dependency_overrides.clear()
