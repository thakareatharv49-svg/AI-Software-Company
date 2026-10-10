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
    production = settings.environment.lower() == "production"
    public_url = settings.public_base_url.strip()
    google_pair = bool(settings.google_oauth_client_id.strip()) and bool(
        settings.google_oauth_client_secret.strip()
    )
    github_pair = bool(settings.github_oauth_client_id.strip()) and bool(
        settings.github_oauth_client_secret.strip()
    )
    google_partial = bool(settings.google_oauth_client_id.strip()) != bool(
        settings.google_oauth_client_secret.strip()
    )
    github_partial = bool(settings.github_oauth_client_id.strip()) != bool(
        settings.github_oauth_client_secret.strip()
    )
    oauth_ready = (google_pair or github_pair) and not google_partial and not github_partial

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
            passed=production,
            message="Production environment selected"
            if production
            else f"Environment is '{settings.environment}'",
        ),
        ReadinessCheck(
            name="oauth_provider_configured",
            passed=oauth_ready,
            message="At least one OAuth provider is fully configured"
            if oauth_ready
            else "Configure a complete Google or GitHub OAuth client ID/secret pair; do not leave partial credentials",
        ),
        ReadinessCheck(
            name="owner_email_configured",
            passed=bool(settings.owner_email.strip()),
            message="Owner email is configured"
            if settings.owner_email.strip()
            else "OWNER_EMAIL is required to provision private company-owner access",
        ),
        ReadinessCheck(
            name="https_and_secure_session_cookie",
            passed=(
                not production
                or (public_url.startswith("https://") and settings.session_cookie_secure)
            ),
            message=(
                "HTTPS public URL and Secure session cookies are enabled"
                if public_url.startswith("https://") and settings.session_cookie_secure
                else "Production requires an HTTPS PUBLIC_BASE_URL and SESSION_COOKIE_SECURE=true"
            ),
        ),
    ]
    return ProductionReadinessReport(
        ready=all(check.passed for check in checks),
        environment=settings.environment,
        checks=checks,
    )
