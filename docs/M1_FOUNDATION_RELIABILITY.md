# M1 Foundation Reliability Audit (M1.1–M1.15)

## Purpose and status

This is a focused revalidation track for the execution foundation of the expanded AI Software Company. The historical M1 milestone remains **COMPLETE** for repository/tooling foundation; this follow-up track is **IN PROGRESS** and must not be represented as complete until every required acceptance gate is supported by test evidence.

**Method:** Waterfall for the ordered audit and acceptance gates; Incremental implementation for small, dependency-ordered changes. Each item must be verified against the live code and CI. Existing code is not considered verified solely because it exists.

## Sub-milestones and acceptance criteria

| Sub-milestone | Scope | Acceptance evidence required | Status at audit start |
|---|---|---|---|
| M1.1 | Baseline and architecture audit | Current execution path, state stores, queue ownership, recovery paths, and known gaps mapped to source/tests | IN PROGRESS |
| M1.2 | Mission lifecycle definitions | Exhaustive status-transition matrix tests; invalid transitions rejected; terminal states remain terminal | IN PROGRESS — transition matrix added in this increment; CI pending |
| M1.3 | Mission persistence | Restart test proves queued/running/terminal records reload with safe normalized state and ownership preserved | IN PROGRESS — SQLite-backed durable store regression tests added; CI pending |
| M1.4 | Queue integrity | Tests prove no silent loss/duplication during enqueue, dequeue, sync failure, and recovery | PARTIALLY IMPLEMENTED — PR #431 addressed per-mission queue-sync failure; broader proof pending |
| M1.5 | Execution recovery | Durable RUNNING jobs recover to QUEUED; interrupted stages reset; valid completed work preserved; queue entry restored | PARTIALLY IMPLEMENTED — PR #432 merged; SQLite-backed persistence/restart regression tests added; full factory restart path pending |
| M1.6 | Stage-level reliability | Stage failure/attempt metadata persists; retry resets only invalid work and preserves valid checkpoints | PARTIALLY IMPLEMENTED — unit coverage exists; real factory-path coverage pending |
| M1.7 | Error isolation | One mission's unexpected failure does not stop later eligible missions; cancellation remains cancellation | PARTIALLY IMPLEMENTED — PR #431 contains isolation logic; extended regression coverage pending |
| M1.8 | Cancellation and stop controls | Stop/cancel tests cover queued and running work, responsive shutdown, and no accidental requeue of explicitly cancelled work | NOT VERIFIED |
| M1.9 | Progress and event tracking | Event/state sequence is consistent with persisted mission state and dashboard progress | NOT VERIFIED |
| M1.10 | Execution diagnostics | Actionable bounded diagnostics are emitted and secrets are redacted across exception, event, and persisted-message paths | PARTIALLY IMPLEMENTED — redaction exists; full-path assertions pending |
| M1.11 | Regression testing | Focused lifecycle/recovery tests plus existing relevant test suites pass on exact PR head | IN PROGRESS |
| M1.12 | Integration validation | Deterministic end-to-end test exercises enqueue → run → failure/recovery → successful retry and records evidence | NOT VERIFIED |
| M1.13 | Security validation | No credential leakage; state transitions and workspace boundaries are enforced by server-side checks | PARTIALLY IMPLEMENTED — secret scan and CodeQL passed on PR #432; broader runtime tests pending |
| M1.14 | Reliability stress testing | Repeated injected failures, restarts, and multiple queued missions do not corrupt state or starve eligible work | NOT VERIFIED |
| M1.15 | M1 acceptance gate | All earlier criteria met; CI, secret scan, dependency audit, CodeQL, and end-to-end acceptance evidence are green and recorded | BLOCKED until M1.1–M1.14 are verified |

## Baseline findings

- Mission lifecycle is represented by `MissionJobStatus` and `transition_job` in `src/company/mission_jobs.py`; tests already cover several valid and invalid paths. The first implementation increment adds a complete public-contract transition matrix.
- Durable RUNNING-job recovery is implemented by `recover_running_job` and the continuous-loop exception path in `src/company/control_center/service.py`. PR #432 passed CI, Secret and Credential Scan, Dependency Vulnerability Audit, and CodeQL on head `1b84db566359b7a4f22548a33833ca227a2c8135`, then merged as `9187746f09a0b6933e6f405075818fc4ceb47fc0`.
- PR #431 isolated per-mission queue synchronization exceptions so later missions can proceed. This is a targeted fix, not a substitute for multi-mission stress testing.
- The current test suite contains unit tests for transition legality, stage recovery, retry behavior, and diagnostic redaction. A full real-factory restart/soak test remains an explicit gap.
- A workflow passing on one commit proves checks for that revision only. Each follow-up PR must validate its own exact head.

## Implementation sequence

1. Complete M1.1 architecture and failure-path inventory, keeping this document current.
2. Complete M1.2 transition contract tests and resolve any mismatch with intended behavior.
3. Implement and test M1.3–M1.5 durable state, queue integrity, and restart recovery as one dependency-aware sequence.
4. Cover stage retries, isolation, cancellation, event consistency, and redaction (M1.6–M1.10).
5. Add deterministic integration and stress tests (M1.11–M1.14).
6. Run the complete M1.15 acceptance gate; do not mark this track complete while any criterion is unverified.

## Evidence ledger

| Evidence | Result |
|---|---|
| PR #431 queue-sync isolation | Merged; multi-mission stress proof still required |
| PR #432 orphaned-mission recovery | Merged as `9187746f09a0b6933e6f405075818fc4ceb47fc0` |
| PR #432 exact-head CI | PASS |
| PR #432 exact-head Secret and Credential Scan | PASS |
| PR #432 exact-head Dependency Vulnerability Audit | PASS |
| PR #432 exact-head CodeQL Security Analysis | PASS |
| New exhaustive lifecycle transition matrix | Merged in PR #433; CI, secret scan, dependency audit, and CodeQL passed on exact head |
| SQLite-backed mission store round-trip/recovery tests | Added in this increment; awaiting CI |\n| Full M1.15 acceptance | NOT YET MET |
