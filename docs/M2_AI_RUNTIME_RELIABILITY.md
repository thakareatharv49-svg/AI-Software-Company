# M2 — AI Runtime Reliability Revalidation

## Purpose and baseline

The original M2 foundation was previously delivered and remains recorded as historically complete. This track verifies that the provider runtime is dependable enough to support autonomous engineering missions. It must not create a second runtime or replace existing provider abstractions without evidence that the current implementation cannot satisfy the contract.

## Waterfall gate

- **Requirements:** each increment has observable acceptance criteria below.
- **Design:** reuse `AIRuntime`, `ModelProvider`, `ModelRequest`, `ModelResponse`, and configured providers.
- **Implementation:** deliver increments in dependency order.
- **Verification:** deterministic tests must not require a live API key or running local model. Provider-dependent smoke checks are optional and explicitly reported separately.
- **Release:** merge only after required CI, Secret and Credential Scan, Dependency Vulnerability Audit, and CodeQL checks pass on the exact PR head.
- **Maintenance:** record residual production/live-provider checks as operational follow-ups rather than claiming them as CI evidence.

## Incremental acceptance ledger

| Increment | Scope | Acceptance evidence | Status |
|---|---|---|---|
| M2.1 | Provider input/configuration and failure contracts | PR #441 merged; CI, Secret Scan, Dependency Audit, and CodeQL passed on the exact head | COMPLETE |
| M2.2 | Ollama HTTP protocol and health behavior | Validate response shape, timeout, HTTP status, transport errors, request payload, and health failures deterministically | IN PROGRESS |
| M2.3 | OpenAI-compatible protocol behavior | Validate completion shape, usage metadata, timeout, malformed JSON, HTTP/transport failures, and auth-header handling | NOT STARTED |
| M2.4 | Shared provider contract and runtime dispatch | Both providers satisfy the same request/response/health contract; configured selection is covered without live credentials | NOT STARTED |
| M2.5 | Cancellation and bounded execution | Cancellation propagates; no accidental retry of cancellation; configured deadlines bound provider calls | NOT STARTED |
| M2.6 | Structured output contract | JSON-mode requests and invalid/missing structured output are handled predictably without silently accepting malformed results | NOT STARTED |
| M2.7 | Diagnostics, metrics, and privacy | Duration/token metadata is bounded and typed; credentials, prompt bodies, and upstream error bodies do not leak into raised errors/logs | NOT STARTED |
| M2.8 | Model readiness and configuration diagnostics | Health/readiness distinguishes endpoint reachability from generation success and reports actionable safe configuration errors | NOT STARTED |
| M2.9 | Real-path integration | Exercise the selected runtime/provider through the company runtime bridge with deterministic HTTP transport; no external model required in default CI | NOT STARTED |
| M2.10 | Final regression and acceptance | Focused tests, full suite, Ruff, diff checks, and all required GitHub security/CI checks pass on merged code | NOT STARTED |

## Acceptance rules

1. Every increment is delivered as a focused, reviewable pull request.
2. Provider errors must not include raw response bodies, credentials, or unredacted request data.
3. HTTP success alone is not model success: responses must have the expected shape and non-empty generated content.
4. Health checks are not proof that generation works; report the distinction explicitly.
5. The default automated suite must be deterministic, network-isolated, and credential-free.
6. A live Ollama/hosted-provider smoke test may be documented as a separate operational check, but is never implied by mocked CI tests.
7. The parent M2 revalidation remains IN PROGRESS until M2.1–M2.10 have evidence and the final acceptance gate is satisfied.

## Evidence policy

For each increment record its PR, merged commit, focused test results, required workflow results, and any residual limitations. Never mark an increment COMPLETE from implementation alone or while required checks are pending/failing.
