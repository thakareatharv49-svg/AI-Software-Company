# R12 — Retry backoff and failure isolation

## Problem

Automatic retries were re-queued fairly, but could become eligible immediately. A repeatedly failing provider or project could therefore consume worker time in a tight retry loop.

## Change

- Persist `retry_not_before_epoch` on each factory project so cooldowns survive snapshot persistence and process restarts.
- Apply capped exponential retry cooldowns: 0.5, 1, 2, 4 seconds and onward, capped at 30 seconds.
- Have `run_next()` skip cooling-down entries and select another eligible queued project.
- When all queued projects are cooling down, `run()` sleeps in bounded intervals until the earliest retry becomes eligible instead of spinning.
- Add tests for cooldown bounds and ensuring a delayed retry yields to a ready project.

GitHub rate-limit failures continue to be blocked for explicit user retry rather than automatically retried.

## Test

```bash
pytest -q tests/unit/company/test_retry_backoff.py tests/unit/company/test_project_factory.py
```

Cooldowns are per-project and in-process scheduling is still single-worker; this does not implement distributed scheduling or shared cross-process coordination.