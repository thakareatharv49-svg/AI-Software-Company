from dataclasses import dataclass
from datetime import UTC, datetime

from src.security.redaction import redact_sensitive_text


@dataclass(frozen=True)
class CompanyEvent:
    event_type: str
    message: str
    project_id: str | None = None
    task_id: str | None = None
    timestamp: datetime = datetime.now(UTC)

    def __post_init__(self) -> None:
        """Sanitize event text before it reaches subscribers or dashboard views."""
        object.__setattr__(
            self,
            "event_type",
            redact_sensitive_text(str(self.event_type))[:120],
        )
        object.__setattr__(
            self,
            "message",
            redact_sensitive_text(str(self.message))[:4000],
        )
        for field_name in ("project_id", "task_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    redact_sensitive_text(str(value))[:300],
                )
