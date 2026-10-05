from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from company.ai.tool_calling import AIToolExchange


@dataclass(frozen=True)
class AIToolAuditEvent:
    """Immutable audit record for an AI tool exchange."""

    tool_name: str
    status: str
    actor: str
    timestamp: str
    output_present: bool
    error_present: bool


class AIToolAuditRecorder:
    """Create safe metadata-only audit events."""

    @staticmethod
    def record(
        exchange: AIToolExchange,
        *,
        actor: str = "ai",
    ) -> AIToolAuditEvent:
        return AIToolAuditEvent(
            tool_name=exchange.result.tool_name,
            status=exchange.result.status,
            actor=actor,
            timestamp=datetime.now(UTC).isoformat(),
            output_present=exchange.result.output is not None,
            error_present=exchange.result.error is not None,
        )

    @staticmethod
    def record_all(
        exchanges: tuple[AIToolExchange, ...],
        *,
        actor: str = "ai",
    ) -> tuple[AIToolAuditEvent, ...]:
        return tuple(
            AIToolAuditRecorder.record(
                exchange,
                actor=actor,
            )
            for exchange in exchanges
        )
