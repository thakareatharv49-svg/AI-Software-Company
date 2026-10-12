from fastapi.testclient import TestClient

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.main import app
from src.security.authorization import require_company_owner


def test_targeted_deletion_removes_only_the_selected_queued_mission():
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
