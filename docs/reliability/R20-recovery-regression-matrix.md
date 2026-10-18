# R20 — Automated Recovery Regression Matrix

## Goal

Exercise recovery invariants across multiple lifecycle states and storage failure points, rather than testing each helper only in isolation.

## Coverage

The regression matrix covers:
- queued and interrupted-running jobs across process restart;
- terminal completed, failed, blocked, and cancelled jobs never being resurrected as queued work;
- preserving completed stages while resetting only interrupted running stages;
- idempotent repeated restore and duplicate queue prevention;
- project snapshot write failure and durable job write failure;
- isolation between missions when one snapshot write fails.

Tests use deterministic in-memory stores and a fake model runtime. They do not require network access or real provider credentials.

## Safety invariants

1. Recovery must not publish a mission to the queue before required persistence succeeds.
2. A running job recovered after restart must have in-flight stages reset to planned and retain completed stage evidence.
3. Terminal jobs must not be resurrected by stale snapshots.
4. One mission's storage failure must not silently prevent unrelated recoverable missions from being considered.
5. Repeated restore must not duplicate a mission.

## Scope

This suite verifies the currently implemented startup recovery contract. It does not claim process-kill testing against a real database, distributed locking, or end-to-end validation of every independent reliability PR. Those require the relevant PRs to be integrated and a durable integration-test environment.
