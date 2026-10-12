from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config.settings import Settings


def test_development_allows_http_localhost_cookie_defaults() -> None:
    settings = Settings(
        _env_file=None,
        environment="development",
        public_base_url="http://localhost:8000",
        session_cookie_secure=False,
    )

    assert settings.environment == "development"


def test_production_rejects_insecure_session_cookie() -> None:
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            public_base_url="https://example.com",
            session_cookie_secure=False,
        )


def test_production_rejects_non_https_public_url() -> None:
    with pytest.raises(ValidationError, match="PUBLIC_BASE_URL"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            public_base_url="http://example.com",
            session_cookie_secure=True,
        )


def test_production_accepts_https_and_secure_cookie() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
            debug=False,
        public_base_url="https://example.com",
        session_cookie_secure=True,
        sandbox_mode="container",
    )

    assert settings.session_cookie_secure is True


def test_production_rejects_host_execution_mode() -> None:
    with pytest.raises(ValidationError, match="SANDBOX_MODE"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            public_base_url="https://example.com",
            session_cookie_secure=True,
            sandbox_mode="host",
        )

def test_company_env_also_activates_production_safety(monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_ACCESS_ENABLED", "false")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://example.com")
    monkeypatch.setenv("SANDBOX_MODE", "host")

    with pytest.raises(ValidationError, match="SANDBOX_MODE"):
        Settings(_env_file=None)



def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(
            _env_file=None,
            environment="production",
            debug=True,
            public_base_url="https://example.com",
            session_cookie_secure=True,
            sandbox_mode="container",
        )


def test_production_rejects_local_access_bypass() -> None:
    with pytest.raises(ValidationError, match="LOCAL_ACCESS_ENABLED"):
        Settings(
            _env_file=None,
            environment="production",
            debug=False,
            local_access_enabled=True,
            public_base_url="https://example.com",
            session_cookie_secure=True,
            sandbox_mode="container",
        )
