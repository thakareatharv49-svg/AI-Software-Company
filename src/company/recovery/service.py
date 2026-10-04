from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RecoveryResult:
    project_id: str | None
    action: str
    retryable: bool
    attempt: int


class RecoveryService:
    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}
        self._failures: list[RecoveryResult] = []

    def record_failure(
        self,
        error: Exception,
        project_id: str | None = None,
    ) -> RecoveryResult:
        key = project_id or "__global__"
        attempt = self._attempts.get(key, 0) + 1
        self._attempts[key] = attempt

        retryable = attempt < self.max_attempts
        action = "retry" if retryable else "block"

        result = RecoveryResult(
            project_id=project_id,
            action=action,
            retryable=retryable,
            attempt=attempt,
        )
        self._failures.append(result)
        return result

    def reset(self, project_id: str | None = None) -> None:
        self._attempts.pop(project_id or "__global__", None)

    def failures(self) -> list[RecoveryResult]:
        return list(self._failures)

    def attempts(self, project_id: str | None = None) -> int:
        return self._attempts.get(project_id or "__global__", 0)
