from __future__ import annotations

import pytest

from src.company.runtime import RuntimeConfig


def test_runtime_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "COMPANY_ENV",
        "COMPANY_HOST",
        "COMPANY_PORT",
        "COMPANY_DEBUG",
        "COMPANY_MAX_CONCURRENT_RUNS",
        "COMPANY_SHUTDOWN_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    config = RuntimeConfig.from_environment()

    assert config.environment == "development"
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.debug is True
    assert config.max_concurrent_runs == 1
    assert config.shutdown_timeout_seconds == 30
    assert config.is_production is False


def test_runtime_config_reads_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANY_ENV", "production")
    monkeypatch.setenv("COMPANY_HOST", "0.0.0.0")
    monkeypatch.setenv("COMPANY_PORT", "9000")
    monkeypatch.setenv("COMPANY_DEBUG", "false")
    monkeypatch.setenv("COMPANY_MAX_CONCURRENT_RUNS", "4")
    monkeypatch.setenv("COMPANY_SHUTDOWN_TIMEOUT_SECONDS", "60")

    config = RuntimeConfig.from_environment()

    assert config.environment == "production"
    assert config.host == "0.0.0.0"
    assert config.port == 9000
    assert config.debug is False
    assert config.max_concurrent_runs == 4
    assert config.shutdown_timeout_seconds == 60
    assert config.is_production is True


def test_invalid_environment_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANY_ENV", "invalid")

    with pytest.raises(ValueError, match="COMPANY_ENV"):
        RuntimeConfig.from_environment()


def test_invalid_integer_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANY_PORT", "abc")

    with pytest.raises(ValueError, match="COMPANY_PORT"):
        RuntimeConfig.from_environment()


def test_production_debug_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANY_ENV", "production")
    monkeypatch.setenv("COMPANY_DEBUG", "true")

    config = RuntimeConfig.from_environment()

    with pytest.raises(
        ValueError,
        match="debug mode must be disabled",
    ):
        config.validate()


def test_port_range_is_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPANY_PORT", "70000")

    config = RuntimeConfig.from_environment()

    with pytest.raises(ValueError, match="65535"):
        config.validate()
