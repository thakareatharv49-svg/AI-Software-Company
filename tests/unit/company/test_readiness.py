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
    report = build_readiness_report()
    assert report.ready is True
    assert all(check.passed for check in report.checks)
