from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True, frozen=True)
class RuntimeDeadline:
    deadline: datetime

    def __post_init__(self) -> None:
        if self.deadline.tzinfo is None:
            raise ValueError("deadline must be timezone-aware")

    @classmethod
    def after(cls, seconds: float) -> RuntimeDeadline:
        if seconds < 0:
            raise ValueError("seconds must be >= 0")

        return cls(
            datetime.now(UTC)
            + __import__("datetime").timedelta(seconds=seconds)
        )

    def remaining_seconds(self) -> float:
        remaining = (
            self.deadline - datetime.now(UTC)
        ).total_seconds()
        return max(0.0, remaining)

    def expired(self) -> bool:
        return self.remaining_seconds() <= 0


@dataclass(slots=True, frozen=True)
class RuntimeDeadlineResult:
    completed: bool
    expired: bool
    remaining_seconds: float


class RuntimeDeadlineController:
    def __init__(self, deadline: RuntimeDeadline) -> None:
        self.deadline = deadline

    async def execute(self, operation) -> RuntimeDeadlineResult:
        remaining = self.deadline.remaining_seconds()

        if remaining <= 0:
            return RuntimeDeadlineResult(
                completed=False,
                expired=True,
                remaining_seconds=0.0,
            )

        try:
            await asyncio.wait_for(operation(), timeout=remaining)
        except TimeoutError:
            return RuntimeDeadlineResult(
                completed=False,
                expired=True,
                remaining_seconds=0.0,
            )

        return RuntimeDeadlineResult(
            completed=True,
            expired=False,
            remaining_seconds=self.deadline.remaining_seconds(),
        )
