# R9 — Execution recovery and idempotency

## Problem

A factory can be driven by a background worker and direct execution calls. Without a single active-project guard, overlapping `run_next` coroutines could claim separate queue entries at once. A stale in-memory queue entry can also outlive its durable mission job and accidentally repeat work that has already been claimed or completed.

## Guarantees

- A second `run_next` call is rejected while this factory instance already has an active project; it does not consume a queue entry or increment attempts.
- Before claiming a queued project, the factory checks the durable mission-job lifecycle.
- If the durable job is no longer `QUEUED`, the stale local queue entry is discarded rather than executed again. The durable job is left unchanged.
- The durable mission-job store remains the lifecycle authority; this is an in-process execution guard, not a distributed lock between separate factory processes.

## Regression coverage

`tests/unit/company/test_execution_recovery_idempotency.py` covers concurrent-entry rejection and stale queue entries whose durable job is already completed.

Run:

```bash
pytest -q tests/unit/company/test_execution_recovery_idempotency.py tests/unit/company/test_project_factory.py tests/unit/company/test_mission_jobs.py
```

CI must pass against the exact pull-request head SHA before this change is considered validated.