from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.dashboard.routes.routes import router
from src.events.service.factory import get_event_service


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_dashboard_health() -> None:
    client = TestClient(create_app())

    response = client.get("/dashboard/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dashboard_summary() -> None:
    get_event_service().clear()
    client = TestClient(create_app())

    response = client.get("/dashboard/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["projects"] == 0
    assert data["agents"] == 0
    assert data["tasks"] == 0
    assert data["memories"] == 0
