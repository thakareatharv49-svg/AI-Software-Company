from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().lower()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a boolean value")


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if parsed < minimum:
        raise ValueError(f"{name} must be >= {minimum}")

    return parsed


@dataclass(slots=True, frozen=True)
class RuntimeConfig:
    environment: str
    host: str
    port: int
    debug: bool
    max_concurrent_runs: int
    shutdown_timeout_seconds: int

    @classmethod
    def from_environment(cls) -> RuntimeConfig:
        environment = os.getenv("COMPANY_ENV", "development").strip().lower()

        if environment not in {"development", "test", "production"}:
            raise ValueError(
                "COMPANY_ENV must be development, test, or production"
            )

        return cls(
            environment=environment,
            host=os.getenv("COMPANY_HOST", "127.0.0.1").strip(),
            port=_env_int("COMPANY_PORT", 8000, 1),
            debug=_env_bool("COMPANY_DEBUG", environment != "production"),
            max_concurrent_runs=_env_int(
                "COMPANY_MAX_CONCURRENT_RUNS",
                1,
                1,
            ),
            shutdown_timeout_seconds=_env_int(
                "COMPANY_SHUTDOWN_TIMEOUT_SECONDS",
                30,
                1,
            ),
        )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate(self) -> None:
        if not self.host:
            raise ValueError("COMPANY_HOST must not be empty")

        if self.is_production and self.debug:
            raise ValueError("debug mode must be disabled in production")

        if self.port > 65535:
            raise ValueError("COMPANY_PORT must be <= 65535")
