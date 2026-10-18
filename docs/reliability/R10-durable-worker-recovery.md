# R10 — Durable worker recovery

## Problem

Factory startup validates the durable mission identity index before recovering orphaned jobs. Previously, it enumerated the durable job store for validation and enumerated it again for recovery. A mutable/custom store could return different records on the second call, meaning recovery might enqueue a job from an identity index that was never validated.

## Change

- Capture one durable-job enumeration during identity preflight.
- Reuse that exact validated snapshot for orphan recovery instead of querying the store a second time.
- Fail closed for orphan recovery if no validated enumeration is available.
- Add a regression test with a store that intentionally changes its response on a second enumeration.

This prevents a validation/recovery time-of-check/time-of-use gap. It does not claim to provide a cross-process lock; concurrent writers still need atomic claims if multiple independent workers share a store.

## Test

```bash
pytest -q tests/unit/company/test_durable_worker_recovery.py tests/unit/company/test_project_factory.py tests/unit/company/test_mission_jobs.py
```

CI and security checks must pass on the exact pull-request head SHA before this change is considered validated.