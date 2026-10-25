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
| M2.1 | Provider input/configuration and failure contracts | PR #441; merge `5e13023537d81ed146ed921f2eaf9c99c0737de0`; all required checks passed on exact head | COMPLETE |
| M2.2 | Ollama HTTP protocol and health behavior | PR #442; merge `25ff25cec60297002afe4b7ad2f1e408971447ad`; all required checks passed on exact head | COMPLETE |
| M2.3 | OpenAI-compatible protocol behavior | PR #446; merge `4565397391d09b836286cab215cc46a33b68250c`; all required checks passed on exact head | COMPLETE |
| M2.4 | Shared provider contract and runtime dispatch | PR #444; merge `d5478bf5f7a5fe63c73e5decd34558b6ab8623ce`; all required checks passed on exact head | COMPLETE |
| M2.5 | Cancellation and bounded execution | PR #445; merge `8bb020b8fd5eb025c7573d17607890b8cee17fe6`; Ruff, full tests, Secret Scan, Dependency Audit, and CodeQL passed after fixing an import-order failure | COMPLETE |
| M2.6 | Structured output contract | PR #447; merge `bb1480a42cafc85f0aff1970697d27d58f74a2f6`; all required checks passed on exact head | COMPLETE |
| M2.7 | Diagnostics, metrics, and privacy | PR #449; merge `3cc07176a32f4a1d4cf3deed9e7fd8c061dff71d`; all required checks passed on exact head | COMPLETE |
| M2.8 | Model readiness and configuration diagnostics | PR #448; merge `3cc58a9ddf31c700e247900368b2336188276bfd`; all required checks passed on exact head | COMPLETE |
| M2.9 | Real-path integration | PR #450; merge `7e42888b81160790887d4a6f4e4a8af52df89dab`; real factory dispatch tested for both providers using deterministic HTTP transport; all required checks passed on exact head | COMPLETE |
| M2.10 | Final regression and acceptance | PR #451: full CI including diff check, Ruff, compile, browser JS syntax, sandbox build, full pytest, Secret Scan, Dependency Audit, and CodeQL all passed on exact head before merge | COMPLETE |

## Acceptance rules

1. Every increment is delivered as a focused, reviewable pull request.
2. Provider errors must not include raw response bodies, credentials, or unredacted request data.
3. HTTP success alone is not model success: responses must have the expected shape and non-empty generated content.
4. Health checks are not proof that generation works; report the distinction explicitly.
5. The default automated suite must be deterministic, network-isolated, and credential-free.
6. A live Ollama/hosted-provider smoke test may be documented as a separate operational check, but is never implied by mocked CI tests.
7. M2 revalidation is COMPLETE for the defined automated acceptance scope after M2.1–M2.10 passed their required checks.

## Evidence policy

For each increment record its PR, merged commit, focused test results, required workflow results, and any residual limitations. Never mark an increment COMPLETE from implementation alone or while required checks are pending/failing.


## Final acceptance result

**M2.1–M2.10: COMPLETE for automated acceptance.** The acceptance record is backed by merged PRs #441, #442, #446, #444, #445, #447, #449, #448, #450, and the final acceptance PR #451. The exact PR heads passed the repository's required checks before merge.

**Explicitly not claimed:** no live Ollama daemon or hosted-provider generation smoke test was run as part of this GitHub-only validation; no production-duration soak, live deployment monitoring, or production latency SLO measurement was performed. Those remain operational follow-ups. Deterministic HTTP mocks prove request/response and factory dispatch behavior, not the quality or availability of a live model.
