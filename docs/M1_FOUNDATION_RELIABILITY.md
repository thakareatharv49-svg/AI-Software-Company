# M1 Foundation Reliability Audit (M1.1–M1.15)

## Purpose and status

This is a focused revalidation track for the execution foundation of the expanded AI Software Company. The historical M1 milestone remains **COMPLETE** for repository/tooling foundation; this follow-up track is **IN PROGRESS** and must not be represented as complete until every required acceptance gate is supported by test evidence.

**Method:** Waterfall for the ordered audit and acceptance gates; Incremental implementation for small, dependency-ordered changes. Each item must be verified against the live code and CI. Existing code is not considered verified solely because it exists.

## Sub-milestones and acceptance criteria

| Sub-milestone | Scope | Acceptance evidence required | Status at audit start |
|---|---|---|---|
| M1.1 | Baseline and architecture audit | Current execution path, state stores, queue ownership, recovery paths, and known gaps mapped to source/tests | COMPLETE — source and regression coverage reviewed; remaining production-operational risks explicitly documented |
| M1.2 | Mission lifecycle definitions | Exhaustive status-transition matrix tests; invalid transitions rejected; terminal states remain terminal | COMPLETE — 36 transition combinations covered in PR #433 |
| M1.3 | Mission persistence | Restart test proves queued/running/terminal records reload with safe normalized state and ownership preserved | COMPLETE for automated acceptance — SQLite round-trip/recovery tests in PR #434 and fresh-store restart integration in PR #438 |
| M1.4 | Queue integrity | Tests prove no silent loss/duplication during enqueue, dequeue, sync failure, and recovery | COMPLETE for deterministic acceptance — PR #431 queue-sync isolation; PR #435 seven-mission failure stress test |
| M1.5 | Execution recovery | Durable RUNNING jobs recover to QUEUED; interrupted stages reset; valid completed work preserved; queue entry restored | COMPLETE for automated acceptance — PR #432 recovery and PR #438 fresh-store factory restoration test |
| M1.6 | Stage-level reliability | Stage failure/attempt metadata persists; retry resets only invalid work and preserves valid checkpoints | COMPLETE for tested paths — retry/checkpoint tests plus cancellation recovery in PR #439 |
| M1.7 | Error isolation | One mission's unexpected failure does not stop later eligible missions; cancellation remains cancellation | COMPLETE for deterministic acceptance — PR #431 exception isolation and PR #435 multi-mission stress test |
| M1.8 | Cancellation and stop controls | Stop/cancel tests cover queued and running work, responsive shutdown, and no accidental requeue of explicitly cancelled work | COMPLETE for tested paths — queued cancellation coverage and running-worker cancellation/recovery in PR #439 |
| M1.9 | Progress and event tracking | Event/state sequence is consistent with persisted mission state and dashboard progress | COMPLETE for tested projection path — PR #437 verifies durable state refreshes the dashboard mission record |
| M1.10 | Execution diagnostics | Actionable bounded diagnostics are emitted and secrets are redacted across exception, event, and persisted-message paths | COMPLETE for tested paths — redaction/bounds tests and continuous-loop diagnostic regression coverage |
| M1.11 | Regression testing | Focused lifecycle/recovery tests plus existing relevant test suites pass on exact PR head | COMPLETE — full CI quality suite passed for the listed reliability PR heads |
| M1.12 | Integration validation | Deterministic end-to-end test exercises enqueue → run → failure/recovery → successful retry and records evidence | COMPLETE for automated integration scope — PR #438 exercises actual ProjectFactory and durable stores across store close/reopen |
| M1.13 | Security validation | No credential leakage; state transitions and workspace boundaries are enforced by server-side checks | COMPLETE for this increment's acceptance scope — secret scan, dependency audit, and CodeQL passed on each merged PR head; regression tests cover redaction and transition enforcement |
| M1.14 | Reliability stress testing | Repeated injected failures, restarts, and multiple queued missions do not corrupt state or starve eligible work | COMPLETE for deterministic stress scope — PR #435 seven-mission injected-failure test and PR #438 restart/reconciliation test |
| M1.15 | M1 acceptance gate | All earlier criteria met; CI, secret scan, dependency audit, CodeQL, and end-to-end acceptance evidence are green and recorded | COMPLETE for the defined automated acceptance scope — all reliability increments merged after required exact-head checks passed; production-duration soak and real deployment monitoring remain separate operational follow-ups |

## Baseline findings

- Mission lifecycle is represented by `MissionJobStatus` and `transition_job` in `src/company/mission_jobs.py`; tests already cover several valid and invalid paths. PR #433 adds a complete public-contract transition matrix, which passed CI and was merged.
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
| New exhaustive lifecycle transition matrix | PR #433 merged; CI, secret scan, dependency audit, and CodeQL passed on exact head |
| PR #434 durable mission store tests | Merged after CI, secret scan, dependency audit, and CodeQL passed on exact head |\n| PR #435 seven-mission queue failure stress test | Merged after CI, secret scan, dependency audit, and CodeQL passed on exact head |\n| PR #437 dashboard durable-state synchronization test | Merged after CI, secret scan, dependency audit, and CodeQL passed on exact head |\n| PR #438 fresh-store factory restart integration test | Merged after CI, secret scan, dependency audit, and CodeQL passed on exact head |\n| PR #439 running cancellation/checkpoint recovery test | Merged after CI, secret scan, dependency audit, and CodeQL passed on exact head |
| Full M1.15 acceptance | MET for defined automated acceptance scope; production soak and deployment monitoring remain separate follow-ups |
