from pydantic import BaseModel, Field

from src.qa.models.enums import DebugStatus, QATestStatus


class QATestRequest(BaseModel):
    command: list[str]
    working_directory: str
    timeout_seconds: float = Field(default=120.0, gt=0, le=600.0)


class QATestResult(BaseModel):
    status: QATestStatus
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int | None = None


class DebugDiagnosis(BaseModel):
    attempt: int
    test_status: QATestStatus
    error: str
    stdout: str = ""
    stderr: str = ""


class DebugAttempt(BaseModel):
    attempt: int
    test_status: QATestStatus
    error: str = ""
    diagnosis: DebugDiagnosis | None = None
    repair_success: bool | None = None


class DebugResult(BaseModel):
    status: DebugStatus
    attempts: list[DebugAttempt] = Field(default_factory=list)
    final_error: str | None = None
