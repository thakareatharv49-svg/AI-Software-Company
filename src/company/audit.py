from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.security.redaction import redact_sensitive_text, redact_sensitive_value


class MissionAuditEntry(BaseModel):
    id: str
    mission_id: str
    event_type: str
    message: str
    status: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message", mode="before")
    @classmethod
    def redact_audit_message(cls, value: Any) -> Any:
        return redact_sensitive_text(value) if isinstance(value, str) else value

    @field_validator("metadata", mode="before")
    @classmethod
    def redact_audit_metadata(cls, value: Any) -> Any:
        return redact_sensitive_value(value)
