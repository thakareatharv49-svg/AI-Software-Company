"""Bounded, failure-aware retry policy for mission stage execution."""

from enum import StrEnum


MAX_REPAIR_ATTEMPTS = 2


class FailureKind(StrEnum):
    REPAIRABLE = "repairable"
    TRANSIENT = "transient"
    NON_RETRYABLE = "non_retryable"


# These errors require a configuration, permission, or provider-side change.
# Repeating an agent prompt cannot safely resolve them and may amplify limits.
_NON_RETRYABLE_MARKERS = (
    "secondary rate limit",
    "temporarily blocked from content creation",
    "rate limit exceeded",
    "too many requests",
    "github api 403",
    "unauthorized",
    "invalid api key",
    "authentication failed",
    "permission denied",
    "forbidden",
    "insufficient permissions",
    "invalid credentials",
    "quota exceeded",
)

_TRANSIENT_MARKERS = (
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "network is unreachable",
    "connection error",
    "try again later",
)


def classify_failure(error: object) -> FailureKind:
    """Classify an untrusted failure string without throwing on malformed input.

    Non-retryable provider/configuration errors take precedence over generic
    transient markers, preventing an auth/rate-limit failure from being retried
    just because its message also mentions a timeout.
    """
    message = str(error or "").strip().casefold()
    if not message:
        return FailureKind.REPAIRABLE
    if any(marker in message for marker in _NON_RETRYABLE_MARKERS):
        return FailureKind.NON_RETRYABLE
    if any(marker in message for marker in _TRANSIENT_MARKERS):
        return FailureKind.TRANSIENT
    # Ordinary agent output, generated-code failures, and QA/test diagnostics
    # may benefit from a targeted correction using the exact previous error.
    return FailureKind.REPAIRABLE


def bounded_repair_attempts(value: object) -> int:
    """Clamp runtime configuration to a small, non-negative hard ceiling."""
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return MAX_REPAIR_ATTEMPTS
    return min(MAX_REPAIR_ATTEMPTS, max(0, parsed))
