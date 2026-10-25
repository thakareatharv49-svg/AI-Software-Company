import math
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Software Developer"
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "COMPANY_ENV"),
    )
    debug: bool = True
    log_level: str = "INFO"
    # Explicit opt-in for a single-user local instance; never enabled by default.
    local_access_enabled: bool = False

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_software_company"
    )

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout: float = 600.0

    # Select the factory generation backend without changing mission code. The
    # OpenAI-compatible option supports hosted APIs and self-hosted gateways.
    factory_model_provider: str = "ollama"
    openai_compatible_base_url: str = "https://api.openai.com/v1"
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = "gpt-4o-mini"
    openai_compatible_timeout: float = 600.0

    # Untrusted generated code must use the isolated backend outside development.
    sandbox_mode: str = "container"
    sandbox_container_image: str = "ai-software-company-sandbox:latest"
    factory_start_paused: bool = False

    # Hard cap protects local model context, disk usage, and generation time.
    factory_max_generated_project_files: int = Field(default=40, ge=4, le=200)
    # Bound total generation time across all model calls, retries, and repair attempts.
    factory_max_generation_seconds: int = Field(default=1800, ge=60, le=7200)
    # Bound model-call amplification when a large project repeatedly needs repair.
    factory_max_generation_model_calls: int = Field(default=50, ge=1, le=200)
    # Bound parallel agent work to avoid overwhelming local models and services.
    factory_max_parallel_tasks: int = Field(default=2, ge=1, le=8)
    # Prevent unattended continuous mode from accumulating an unbounded durable queue.
    factory_max_queued_missions: int = Field(default=500, ge=1, le=500)
    # Retry transient agent failures, but always cap the number of attempts.
    factory_task_max_attempts: int = Field(default=2, ge=1, le=5)

    github_token: str = ""
    github_api_base_url: str = "https://api.github.com"
    github_timeout: float = 30.0
    github_allow_writes: bool = False
    github_repository_owner: str = ""
    github_repository_name: str = ""
    github_project_private: bool = False
    github_default_branch: str = "main"
    github_branch_prefix: str = "factory"

    # Customer sign-in. Keep these credentials server-side in environment variables.
    public_base_url: str = "http://localhost:8000"
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    owner_email: str = ""
    session_cookie_secure: bool = False

    # Dedicated read-only status endpoint for Nexora HQ; never grants mission access.
    nexora_hq_status_token: str = ""

    @field_validator("factory_model_provider")
    @classmethod
    def validate_factory_model_provider(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if normalized not in {"ollama", "openai-compatible", "openai_compatible"}:
            raise ValueError(
                "FACTORY_MODEL_PROVIDER must be 'ollama' or 'openai-compatible'"
            )
        return normalized

    @field_validator("ollama_timeout", "openai_compatible_timeout")
    @classmethod
    def validate_model_provider_timeout(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Model provider timeout must be a finite positive number")
        return value

    @field_validator("ollama_model", "openai_compatible_model")
    @classmethod
    def validate_model_provider_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Model provider model name cannot be empty")
        return value.strip()

    @field_validator("ollama_base_url", "openai_compatible_base_url")
    @classmethod
    def validate_model_provider_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        try:
            parsed = urlsplit(normalized)
            valid = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(
                "Model provider URL must be an HTTP(S) URL without embedded credentials"
            )
        return normalized

    @field_validator("nexora_hq_status_token")
    @classmethod
    def validate_nexora_hq_status_token(cls, value: str) -> str:
        if value and len(value) < 32:
            raise ValueError("NEXORA_HQ_STATUS_TOKEN must contain at least 32 characters")
        return value

    @field_validator("sandbox_mode")
    @classmethod
    def validate_sandbox_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"host", "container"}:
            raise ValueError("SANDBOX_MODE must be 'host' or 'container'")
        return normalized

    @model_validator(mode="after")
    def validate_production_cookie_security(self) -> "Settings":
        if self.environment.strip().lower() in {"production", "prod", "staging"}:
            if self.debug:
                raise ValueError("DEBUG must be false outside development")
            if self.local_access_enabled:
                raise ValueError(
                    "LOCAL_ACCESS_ENABLED must be false outside development"
                )
            if not self.session_cookie_secure:
                raise ValueError(
                    "SESSION_COOKIE_SECURE must be true outside development"
                )
            if not self.public_base_url.strip().lower().startswith("https://"):
                raise ValueError(
                    "PUBLIC_BASE_URL must use HTTPS outside development"
                )
            if self.sandbox_mode != "container":
                raise ValueError(
                    "SANDBOX_MODE must be container outside development"
                )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()
