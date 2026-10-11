from types import SimpleNamespace

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from config.settings import Settings, settings
from src.company.mission_jobs import MissionJobStatus
from src.main import app
from src.api.routes.hq_status import get_hq_status_control_center


TOKEN = "test-nexora-hq-service-token-32-characters"


class FakeControlCenter:
    def mission_jobs(self):
        return [
            SimpleNamespace(status=MissionJobStatus.RUNNING),
            SimpleNamespace(status=MissionJobStatus.QUEUED),
            SimpleNamespace(status=MissionJobStatus.COMPLETED),
            SimpleNamespace(status=MissionJobStatus.BLOCKED),
            SimpleNamespace(status=MissionJobStatus.FAILED),
            SimpleNamespace(status=MissionJobStatus.CANCELLED),
        ]


@pytest.fixture
def client():
    app.dependency_overrides[get_hq_status_control_center] = FakeControlCenter
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_hq_status_is_not_exposed_when_service_token_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "nexora_hq_status_token", "")

    response = client.get("/api/hq/status", headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 503
    assert response.json() == {"detail": "HQ status integration is not configured"}


@pytest.mark.parametrize(
    "authorization",
    ["", "Basic something", "Bearer wrong-token"],
)
def test_hq_status_rejects_missing_or_invalid_service_token(client, monkeypatch, authorization):
    monkeypatch.setattr(settings, "nexora_hq_status_token", TOKEN)
    headers = {"Authorization": authorization} if authorization else {}

    response = client.get("/api/hq/status", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid service credentials"}


def test_hq_status_returns_only_aggregate_read_only_counts(client, monkeypatch):
    monkeypatch.setattr(settings, "nexora_hq_status_token", TOKEN)

    response = client.get("/api/hq/status", headers={"Authorization": f"Bearer {TOKEN}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "ai-software-developer"
    assert payload["status"] == "degraded"
    assert payload["active_missions"] == 1
    assert payload["queued_missions"] == 1
    assert payload["completed_missions"] == 1
    assert payload["blocked_missions"] == 1
    assert payload["updated_at"].endswith("+00:00")
    assert "mission" not in payload
    assert TOKEN not in response.text


def test_hq_status_token_must_be_long_enough():
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(nexora_hq_status_token="too-short")
