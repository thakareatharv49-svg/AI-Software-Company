from __future__ import annotations

from pydantic import BaseModel

from src.config.settings import settings


class ReadinessCheck(BaseModel):
    name: str
    passed: bool
    message: str


class ProductionReadinessReport(BaseModel):
    ready: bool
    environment: str
    checks: list[ReadinessCheck]


def build_readiness_report() -> ProductionReadinessReport:
    checks = [
        ReadinessCheck(
            name="debug_disabled",
            passed=not settings.debug,
            message="Debug mode is disabled" if not settings.debug else "Debug mode is enabled",
        ),
        ReadinessCheck(
            name="database_configured",
            passed=bool(settings.database_url.strip()),
            message="Database URL is configured"
            if settings.database_url.strip()
            else "Database URL is missing",
        ),
        ReadinessCheck(
            name="ai_runtime_configured",
            passed=bool(settings.ollama_base_url.strip() and settings.ollama_model.strip()),
            message="AI runtime endpoint and model are configured"
            if settings.ollama_base_url.strip() and settings.ollama_model.strip()
            else "AI runtime endpoint or model is missing",
        ),
        ReadinessCheck(
            name="github_writes_explicit",
            passed=not settings.github_allow_writes or bool(settings.github_token.strip()),
            message=(
                "GitHub writes are disabled or authenticated"
                if not settings.github_allow_writes or settings.github_token.strip()
                else "GitHub writes are enabled without a token"
            ),
        ),
        ReadinessCheck(
            name="production_environment",
            passed=settings.environment.lower() == "production",
            message=(
                "Production environment selected"
                if settings.environment.lower() == "production"
                else f"Environment is '{settings.environment}'"
            ),
        ),
    ]
    return ProductionReadinessReport(
        ready=all(check.passed for check in checks),
        environment=settings.environment,
        checks=checks,
    )
