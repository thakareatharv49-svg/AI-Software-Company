import pytest

from src.company.retry_policy import FailureClass, classify_failure


@pytest.mark.parametrize(
    "message",
    [
        "TimeoutError: request exceeded deadline",
        "Connection reset by peer",
        "HTTP 503 service unavailable",
        "provider temporarily unavailable",
        "HTTP 429 rate limit exceeded",
    ],
)
def test_classifies_transient_provider_failures(message):
    assert classify_failure(message) == FailureClass.TRANSIENT


@pytest.mark.parametrize(
    "message",
    [
        "Authentication failed: invalid API key",
        "HTTP 401 unauthorized",
        "Permission denied for this model",
        "Unsupported provider selected",
        "Model does not exist",
        "Missing required configuration",
    ],
)
def test_classifies_non_retryable_configuration_and_access_failures(message):
    assert classify_failure(message) == FailureClass.NON_RETRYABLE


@pytest.mark.parametrize(
    "message",
    [
        "SyntaxError: invalid generated source",
        "ImportError: generated package is missing",
        "Acceptance tests failed",
        "Unexpected stage result",
        "",
        None,
    ],
)
def test_defaults_unknown_and_repairable_failures_to_bounded_repair(message):
    assert classify_failure(message) == FailureClass.REPAIRABLE


def test_authentication_marker_takes_precedence_over_generic_http_status():
    assert classify_failure("HTTP 403: invalid API key") == FailureClass.NON_RETRYABLE
