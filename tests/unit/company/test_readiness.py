from src.company.readiness import build_readiness_report
from src.config.settings import settings


def test_readiness_report_fails_safe_for_development(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "debug", True)
    monkeypatch.setattr(settings, "github_allow_writes", False)
    report = build_readiness_report()
    assert report.ready is False
    assert any(check.name == "debug_disabled" and not check.passed for check in report.checks)
    assert any(check.name == "production_environment" and not check.passed for check in report.checks)


def test_readiness_report_passes_for_authenticated_production(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "database_url", "postgresql+asyncpg://db")
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama")
    monkeypatch.setattr(settings, "ollama_model", "model")
    monkeypatch.setattr(settings, "github_allow_writes", True)
    monkeypatch.setattr(settings, "github_token", "token")
    monkeypatch.setattr(settings, "google_oauth_client_id", "google-client")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "google-secret")
    monkeypatch.setattr(settings, "github_oauth_client_id", "")
    monkeypatch.setattr(settings, "github_oauth_client_secret", "")
    monkeypatch.setattr(settings, "owner_email", "owner@example.com")
    monkeypatch.setattr(settings, "public_base_url", "https://company.example.com")
    monkeypatch.setattr(settings, "session_cookie_secure", True)
    report = build_readiness_report()
    assert report.ready is True
    assert all(check.passed for check in report.checks)


def test_readiness_rejects_insecure_production_oauth_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "public_base_url", "http://company.example.com")
    monkeypatch.setattr(settings, "session_cookie_secure", False)
    monkeypatch.setattr(settings, "owner_email", "")
    monkeypatch.setattr(settings, "google_oauth_client_id", "client-only")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "")
    monkeypatch.setattr(settings, "github_oauth_client_id", "")
    monkeypatch.setattr(settings, "github_oauth_client_secret", "")
    report = build_readiness_report()
    failed = {check.name for check in report.checks if not check.passed}
    assert "https_and_secure_session_cookie" in failed
    assert "owner_email_configured" in failed
    assert "oauth_provider_configured" in failed


def test_readiness_api_is_exposed() -> None:
    from fastapi.testclient import TestClient

    from src.main import app

    response = TestClient(app).get("/api/company/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert "ready" in payload
    assert "checks" in payload
