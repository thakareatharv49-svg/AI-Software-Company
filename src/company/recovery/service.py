from dataclasses import dataclass
import re


@dataclass(slots=True, frozen=True)
class RecoveryResult:
    project_id: str | None
    action: str
    retryable: bool
    attempt: int
    stage: str | None = None
    error_type: str = "Exception"
    error_message: str = ""
    repeated_failure: bool = False


class RecoveryService:
    """Track retry budgets and actionable diagnostics per project and stage."""

    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}
        self._failures: list[RecoveryResult] = []
        self._last_error_signature: dict[str, tuple[str, str]] = {}

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

        error_type = type(error).__name__
        error_message = str(error)[:2000]
        normalized_message = re.sub(
            r"for project [^:]+:",
            "for project <id>:",
            error_message,
            flags=re.IGNORECASE,
        )
        signature = (error_type, " ".join(normalized_message.casefold().split()))
        # Only suppress deterministic validation failures. Infrastructure, execution,
        # and reviewer errors can be transient even when their messages are identical.
        repeated_failure = (
            stage in {"qa", "artifacts"}
            and self._last_error_signature.get(key) == signature
        )
        self._last_error_signature[key] = signature
        retryable = attempt < self.max_attempts and not repeated_failure
        if repeated_failure:
            action = "block_repeated_failure"
        else:
            action = "retry" if retryable else "block"
        result = RecoveryResult(
            project_id=project_id,
            action=action,
            retryable=retryable,
            attempt=attempt,
            stage=stage,
            error_type=error_type,
            error_message=error_message,
            repeated_failure=repeated_failure,
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
            key = self._key(project_id, stage)
            self._attempts.pop(key, None)
            self._last_error_signature.pop(key, None)
            return

        project = project_id or "__global__"
        prefix = f"{project}::"
        for key in list(self._attempts):
            if key.startswith(prefix):
                self._attempts.pop(key, None)
                self._last_error_signature.pop(key, None)

    def failures(self) -> list[RecoveryResult]:
        return list(self._failures)

    def attempts(
        self,
        project_id: str | None = None,
        stage: str | None = None,
    ) -> int:
        return self._attempts.get(self._key(project_id, stage), 0)
