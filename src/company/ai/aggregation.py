from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from company.ai.tool_calling import AIToolExchange


@dataclass(frozen=True)
class AIToolSummary:
    """Safe aggregate of tool-call execution results."""

    total: int
    successful: int
    failed: int
    denied: int
    outputs: tuple[Any, ...]


class AIToolResultAggregator:
    """Aggregate M22 exchanges without changing execution semantics."""

    @staticmethod
    def summarize(
        exchanges: tuple[AIToolExchange, ...],
    ) -> AIToolSummary:
        successful = sum(
            exchange.result.status == "success"
            for exchange in exchanges
        )
        denied = sum(
            exchange.result.status == "denied"
            for exchange in exchanges
        )
        failed = sum(
            exchange.result.status == "failure"
            for exchange in exchanges
        )

        return AIToolSummary(
            total=len(exchanges),
            successful=successful,
            failed=failed,
            denied=denied,
            outputs=tuple(
                exchange.result.output
                for exchange in exchanges
                if exchange.result.status == "success"
            ),
        )
