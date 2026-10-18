"""Conservative failure classification for bounded factory retries."""

from __future__ import annotations

from enum import StrEnum


class FailureClass(StrEnum):
    """Operational class used to decide whether another attempt is worthwhile."""

    TRANSIENT = "transient"
    REPAIRABLE = "repairable"
    NON_RETRYABLE = "non_retryable"


_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "connection error",
    "temporarily unavailable",
    "temporary failure",
    "server disconnected",
    "http 429",
    "status 429",
    "http 500",
    "http 502",
    "http 503",
    "http 504",
    "service unavailable",
    "gateway timeout",
    "rate limit",
)

_NON_RETRYABLE_MARKERS = (
    "invalid api key",
    "incorrect api key",
    "authentication failed",
    "unauthorized",
    "http 401",
    "status 401",
    "permission denied",
    "forbidden",
    "http 403",
    "status 403",
    "unsupported provider",
    "unsupported model",
    "model does not exist",
    "unknown model",
    "missing required configuration",
    "configuration is missing",
)


def classify_failure(error: object) -> FailureClass:
    """Classify an error message without exposing or persisting raw exception data.

    Unknown errors default to repairable so existing bounded retry behavior is
    preserved while the factory gathers more evidence. Explicit auth, permission,
    and unsupported-configuration failures are not retried blindly. Transient
    network/service failures are distinguished for backoff and operator guidance.
    """
    text = str(error or "").strip().lower()
    if any(marker in text for marker in _NON_RETRYABLE_MARKERS):
        return FailureClass.NON_RETRYABLE
    if any(marker in text for marker in _TRANSIENT_MARKERS):
        return FailureClass.TRANSIENT
    return FailureClass.REPAIRABLE
