from pydantic import BaseModel, Field

from src.sandbox.models.enums import SandboxStatus


class SandboxLimits(BaseModel):
    timeout_seconds: float = Field(default=30.0, gt=0, le=300.0)
    max_output_bytes: int = Field(default=100_000, gt=0, le=1_000_000)


class SandboxRequest(BaseModel):
    command: list[str]
    working_directory: str
    limits: SandboxLimits = Field(default_factory=SandboxLimits)


class SandboxResult(BaseModel):
    status: SandboxStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int | None = None
    error: str | None = None
