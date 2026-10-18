# R15 — Classified Failure Recovery

## Goal

Avoid wasting bounded retry attempts on errors that another identical run cannot fix, while preserving repair attempts for generated-code and acceptance failures.

## Failure classes

- `transient`: timeouts, connection failures, service unavailability, and common 429/5xx responses. These remain eligible for the existing bounded retry path and retry backoff.
- `repairable`: syntax/import/acceptance failures and unknown errors. Unknowns intentionally remain repairable for compatibility; the factory can feed the failure detail into the next attempt.
- `non_retryable`: explicit authentication, permission, unsupported provider/model, and missing-configuration errors. The factory blocks these immediately and records a clear lifecycle transition instead of repeating a doomed request.

## Integration

`src/company/retry_policy.py` exposes `FailureClass` and `classify_failure()`. `ProjectFactory` consults the classification in both orchestrator-blocked and execution-error paths. Existing GitHub secondary-rate-limit handling remains first so the factory does not repeatedly hammer a rate-limited GitHub API.

The classifier works on error text and does not persist raw exception objects. It is deliberately conservative: ambiguous messages default to repairable, still subject to the existing retry limit. This is not a replacement for provider-specific structured error codes; adding those should be done when adapters expose stable codes.

## Tests

`tests/unit/company/test_retry_policy.py` covers transient failures, permanent access/configuration failures, repairable generated-code errors, unknown errors, and marker precedence.
