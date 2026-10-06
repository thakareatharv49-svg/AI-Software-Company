from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Callable

@dataclass(frozen=True, slots=True)
class DebugAttempt:
    attempt: int
    success: bool
    error: str = ""

class DebuggingService:
    """Runs bounded repair attempts while preserving failure history."""
    def __init__(self, max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts

    def run(self, operation: Callable[[], object]) -> tuple[DebugAttempt, ...]:
        attempts = []
        for number in range(1, self.max_attempts + 1):
            try:
                operation()
            except Exception as exc:
                attempts.append(DebugAttempt(number, False, str(exc)))
            else:
                attempts.append(DebugAttempt(number, True))
                break
        return tuple(attempts)
