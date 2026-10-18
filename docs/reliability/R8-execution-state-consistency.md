# R8 — Execution-state consistency

## Problem

Factory progress is represented in both the durable mission-job store and the project snapshot store. Restore treats the mission job as authoritative and uses it to repair a stale or missing snapshot. Previously, live stage progress wrote the project snapshot first and the durable job second. A crash or durable-job write failure between those writes could leave the snapshot ahead of the authoritative record; a later restart could then discard progress that had appeared in the dashboard.

## Change

- Persist the authoritative mission-job plan first.
- Persist the project snapshot only after the durable job write succeeds.
- If the snapshot write fails after the job write succeeds, restore can rebuild the snapshot from the newer durable job.
- If the durable job write fails, do not publish a newer snapshot that restore would later overwrite.

This is an ordering guarantee, not a cross-store transaction. It relies on the existing restore contract that the durable mission job is authoritative.

## Regression coverage

`tests/unit/company/test_execution_state_consistency.py` verifies both the successful write order and that a failed durable write prevents a newer project snapshot from being published.

Run:

```bash
pytest -q tests/unit/company/test_execution_state_consistency.py tests/unit/company/test_enqueue_preserves_durable_progress.py tests/unit/company/test_mission_jobs.py
```

CI must pass on the pull request's exact head revision before this change is considered validated.