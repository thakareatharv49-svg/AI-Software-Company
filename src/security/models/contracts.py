from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.security.models.enums import ReviewStatus, SecuritySeverity, SecurityStatus


class SecurityAction(StrEnum):
    READ = "read"
    TOOL_EXECUTE = "tool.execute"
    GITHUB_READ = "github.read"
    GITHUB_WRITE = "github.write"
    SHELL_EXECUTE = "shell.execute"


class PermissionDecision(BaseModel):
    action: SecurityAction
    allowed: bool
    reason: str


class SecurityPolicy(BaseModel):
    allow_tool_execution: bool = True
    allow_github_writes: bool = False
    allow_shell_execution: bool = False


class SecurityFinding(BaseModel):
    rule: str
    severity: SecuritySeverity
    message: str
    path: str
    line: int | None = None
    recommendation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeReviewRequest(BaseModel):
    project_id: str
    task_id: str | None = None
    working_directory: str | None = None
    files: dict[str, str] = Field(default_factory=dict)
    diff: str = ""
    summary: str = ""


class CodeReviewResult(BaseModel):
    approved: bool
    status: ReviewStatus
    findings: list[SecurityFinding] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityScanRequest(BaseModel):
    project_id: str
    task_id: str | None = None
    working_directory: str | None = None
    files: dict[str, str] = Field(default_factory=dict)
    diff: str = ""


class SecurityScanResult(BaseModel):
    status: SecurityStatus
    findings: list[SecurityFinding] = Field(default_factory=list)
