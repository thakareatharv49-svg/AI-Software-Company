from pydantic import BaseModel, Field

from src.security.models.enums import (
    ReviewStatus,
    SecuritySeverity,
    SecurityStatus,
)


class SecurityFinding(BaseModel):
    rule: str
    severity: SecuritySeverity
    message: str
    path: str | None = None
    line: int | None = None


class SecurityScanRequest(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)


class SecurityScanResult(BaseModel):
    status: SecurityStatus
    findings: list[SecurityFinding] = Field(default_factory=list)


class CodeReviewRequest(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)
    summary: str = ""


class CodeReviewResult(BaseModel):
    status: ReviewStatus
    findings: list[SecurityFinding] = Field(default_factory=list)
    summary: str = ""
