from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RecoveryResult:
    project_id: str | None
    action: str
    retryable: bool
    attempt: int
    stage: str | None = None
    error_type: str = "Exception"
    error_message: str = ""


class RecoveryService:
    """Track retry budgets and actionable diagnostics per project and stage."""

    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}
        self._failures: list[RecoveryResult] = []

    @staticmethod
    def _key(project_id: str | None, stage: str | None = None) -> str:
        project = project_id or "__global__"
        normalized_stage = (stage or "__project__").strip().casefold()
        return f"{project}::{normalized_stage}"

    def record_failure(
        self,
        error: Exception,
        project_id: str | None = None,
        stage: str | None = None,
    ) -> RecoveryResult:
        key = self._key(project_id, stage)
        attempt = self._attempts.get(key, 0) + 1
        self._attempts[key] = attempt

        retryable = attempt < self.max_attempts
        action = "retry" if retryable else "block"
        result = RecoveryResult(
            project_id=project_id,
            action=action,
            retryable=retryable,
            attempt=attempt,
            stage=stage,
            error_type=type(error).__name__,
            error_message=str(error)[:2000],
        )
        self._failures.append(result)
        return result

    def reset(
        self,
        project_id: str | None = None,
        stage: str | None = None,
    ) -> None:
        """Reset one stage's budget, or all tracked stages for a project."""
        if stage is not None:
            self._attempts.pop(self._key(project_id, stage), None)
            return

        project = project_id or "__global__"
        prefix = f"{project}::"
        for key in list(self._attempts):
            if key.startswith(prefix):
                self._attempts.pop(key, None)

    def failures(self) -> list[RecoveryResult]:
        return list(self._failures)

    def attempts(
        self,
        project_id: str | None = None,
        stage: str | None = None,
    ) -> int:
        return self._attempts.get(self._key(project_id, stage), 0)
