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
            public_base_url="https://example.com",
            session_cookie_secure=False,
        )


def test_production_rejects_non_https_public_url() -> None:
    with pytest.raises(ValidationError, match="PUBLIC_BASE_URL"):
        Settings(
            _env_file=None,
            environment="production",
            public_base_url="http://example.com",
            session_cookie_secure=True,
        )


def test_production_accepts_https_and_secure_cookie() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
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
            public_base_url="https://example.com",
            session_cookie_secure=True,
            sandbox_mode="host",
        )
