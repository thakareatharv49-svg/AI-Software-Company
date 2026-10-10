from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.company.control_center.routes import get_control_center
from src.main import app
from src.security.customer_authorization import require_customer_workspace


def _job(mission_id: str, workspace_id: str):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=mission_id,
        workspace_id=workspace_id,
        mission=SimpleNamespace(name=f"Mission {mission_id}", objective="Build a product"),
        status=SimpleNamespace(value="queued"),
        message="Mission queued",
        attempts=0,
        created_at=now,
        updated_at=now,
        plan=SimpleNamespace(
            steps=[
                SimpleNamespace(stage="research", status="completed", detail="Research done"),
                SimpleNamespace(stage="execution", status="running", detail="Generating files"),
            ],
            model_dump=lambda mode="json": {"steps": []},
        ),
    )


class _FakeCenter:
    def __init__(self):
        self.owned = _job("owned-mission", "workspace-a")
        self.foreign = _job("foreign-mission", "workspace-b")

    def factory_running(self):
        return False

    def mission_jobs(self):
        return [self.owned, self.foreign]

    def mission_job(self, mission_id: str):
        return {
            self.owned.id: self.owned,
            self.foreign.id: self.foreign,
        }.get(mission_id)

    def project_outputs(self, mission_id: str):
        return []


def test_customer_mission_list_is_workspace_scoped():
    center = _FakeCenter()
    workspace = SimpleNamespace(id="workspace-a")
    app.dependency_overrides[require_customer_workspace] = lambda: (None, workspace)
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        response = TestClient(app).get("/api/customer/missions")
        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["id"] for item in items] == ["owned-mission"]
        assert items[0]["stages"] == [
            {"name": "research", "status": "completed", "detail": "Research done"},
            {"name": "execution", "status": "running", "detail": "Generating files"},
        ]
    finally:
        app.dependency_overrides.clear()


def test_customer_cannot_read_another_workspaces_mission_or_outputs():
    center = _FakeCenter()
    workspace = SimpleNamespace(id="workspace-a")
    app.dependency_overrides[require_customer_workspace] = lambda: (None, workspace)
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        client = TestClient(app)
        assert client.get("/api/customer/missions/foreign-mission").status_code == 404
        assert client.get(
            "/api/customer/missions/foreign-mission/outputs"
        ).status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_customer_cannot_retry_another_workspaces_mission():
    center = _FakeCenter()
    workspace = SimpleNamespace(id="workspace-a")
    app.dependency_overrides[require_customer_workspace] = lambda: (None, workspace)
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        response = TestClient(app).post("/api/customer/missions/foreign-mission/retry")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_customer_cannot_retry_a_queued_mission():
    center = _FakeCenter()
    workspace = SimpleNamespace(id="workspace-a")
    app.dependency_overrides[require_customer_workspace] = lambda: (None, workspace)
    app.dependency_overrides[get_control_center] = lambda: center
    try:
        response = TestClient(app).post("/api/customer/missions/owned-mission/retry")
        assert response.status_code == 409
        assert "queued" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
