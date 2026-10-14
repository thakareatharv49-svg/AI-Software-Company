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
    from src.security.authorization import require_company_owner

    app.dependency_overrides[require_company_owner] = lambda: None
    try:
        response = TestClient(app).get("/api/company/readiness")
        assert response.status_code == 200
        payload = response.json()
        assert "ready" in payload
        assert "checks" in payload
    finally:
        app.dependency_overrides.pop(require_company_owner, None)


@pytest.mark.parametrize(
    ("setting_name", "invalid_value", "check_name"),
    [
        ("debug", True, "debug_disabled"),
        ("database_url", "   ", "database_configured"),
        ("ollama_base_url", "", "ai_runtime_configured"),
        ("ollama_model", "", "ai_runtime_configured"),
        ("github_token", "", "github_writes_explicit"),
        ("environment", "staging", "production_environment"),
        ("google_oauth_client_secret", "", "oauth_provider_configured"),
        ("owner_email", "  ", "owner_email_configured"),
        ("public_base_url", "http://company.example.com", "https_and_secure_session_cookie"),
        ("session_cookie_secure", False, "https_and_secure_session_cookie"),
    ],
)
def test_readiness_fails_closed_for_each_release_blocker(
    monkeypatch,
    setting_name: str,
    invalid_value,
    check_name: str,
) -> None:
    """Each required release condition must independently block readiness."""
    valid_configuration = {
        "environment": "production",
        "debug": False,
        "database_url": "postgresql+asyncpg://db",
        "ollama_base_url": "http://ollama",
        "ollama_model": "model",
        "github_allow_writes": True,
        "github_token": "test-github-token",
        "google_oauth_client_id": "google-client",
        "google_oauth_client_secret": "google-secret",
        "github_oauth_client_id": "",
        "github_oauth_client_secret": "",
        "owner_email": "owner@example.com",
        "public_base_url": "https://company.example.com",
        "session_cookie_secure": True,
    }
    for name, value in valid_configuration.items():
        monkeypatch.setattr(settings, name, value)

    monkeypatch.setattr(settings, setting_name, invalid_value)
    report = build_readiness_report()

    assert report.ready is False
    assert any(
        check.name == check_name and not check.passed
        for check in report.checks
    )


def test_readiness_allows_unauthenticated_github_when_writes_are_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "github_allow_writes", False)
    monkeypatch.setattr(settings, "github_token", "")
    report = build_readiness_report()

    check = next(
        check for check in report.checks if check.name == "github_writes_explicit"
    )
    assert check.passed is True


def test_readiness_report_does_not_expose_credentials(monkeypatch) -> None:
    secrets = {
        "github_token": "never-return-this-github-token",
        "google_oauth_client_secret": "never-return-this-google-secret",
        "github_oauth_client_secret": "never-return-this-oauth-secret",
    }
    for name, value in secrets.items():
        monkeypatch.setattr(settings, name, value)

    report_text = build_readiness_report().model_dump_json()

    for secret in secrets.values():
        assert secret not in report_text
