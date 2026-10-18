# R19 — Recovery Verification and Reconciliation

## Goal

Compare the durable mission job, persisted project snapshot, and in-memory queue to find inconsistent recovery state before another execution attempt.

## API

`ProjectFactory.reconcile_mission(mission_id, repair=False)` reports:
- durable job status;
- number of matching snapshots and in-memory queue entries;
- whether the active worker matches the mission;
- concrete discrepancy codes and a recommended next action.

The default is read-only. Store read failures are reported instead of treated as missing data.

## Conservative repair

With `repair=True`, the only automatic repair is rehydrating a missing in-memory queue entry from one unambiguous, durably `QUEUED` job while the worker is idle. The project snapshot is written before the queue is changed. A post-write verification is still required.

The method refuses to guess when it sees duplicate snapshots, duplicate queue entries, conflicting plan/status data, an active worker, or a durable RUNNING job without a matching active worker. These cases are surfaced for explicit investigation.

## Safety boundary

This is in-process reconciliation, not a distributed lock or transaction across storage systems. It does not retry failed/blocked work or alter terminal job status. Reconciliation does not replace startup restore or durable-store integrity checks.

## Tests

Unit tests cover read-only inspection, safe queue rehydration, conflicting snapshots, duplicate queue entries, missing jobs, and refusal to repair while the worker is active.
