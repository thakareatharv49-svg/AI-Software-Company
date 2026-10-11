from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Software Developer"
    environment: str = "development"
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

    # Hard cap protects local model context, disk usage, and generation time.
    factory_max_generated_project_files: int = Field(default=40, ge=4, le=200)
    # Bound parallel agent work to avoid overwhelming local models and services.
    factory_max_parallel_tasks: int = Field(default=2, ge=1, le=8)
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
