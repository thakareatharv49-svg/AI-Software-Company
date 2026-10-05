from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class AIExecutionContext:
    """Immutable context carried through one AI execution."""

    run_id: str = field(default_factory=lambda: uuid4().hex)
    actor: str = "ai"
    metadata: dict[str, Any] = field(default_factory=dict)
    max_tool_calls: int = 10
    max_rounds: int = 5

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be empty")

        if not self.actor.strip():
            raise ValueError("actor must not be empty")

        if self.max_tool_calls < 0:
            raise ValueError("max_tool_calls must be non-negative")

        if self.max_rounds < 0:
            raise ValueError("max_rounds must be non-negative")

        object.__setattr__(
            self,
            "metadata",
            dict(self.metadata),
        )


class AIExecutionContextFactory:
    """Create isolated execution contexts."""

    @staticmethod
    def create(
        *,
        actor: str = "ai",
        metadata: dict[str, Any] | None = None,
        max_tool_calls: int = 10,
        max_rounds: int = 5,
    ) -> AIExecutionContext:
        return AIExecutionContext(
            actor=actor,
            metadata=dict(metadata or {}),
            max_tool_calls=max_tool_calls,
            max_rounds=max_rounds,
        )
