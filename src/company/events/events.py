from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class CompanyEvent:
    event_type: str
    message: str
    project_id: str | None = None
    task_id: str | None = None
    timestamp: datetime = datetime.now(UTC)
