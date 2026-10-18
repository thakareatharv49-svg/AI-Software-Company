# R11 — Queue fairness and starvation prevention

## Problem

The factory already rotates failed or paused projects to the back of the queue. However, its fairness helper previously did nothing if the same mission ID was already present. A stale duplicate left by interrupted cleanup or recovery could therefore keep a retry near the front, ahead of missions that had been waiting longer.

## Change

- Every retry/pause requeue now removes all existing entries for that mission ID and appends the current project exactly once at the tail.
- Existing FIFO order among other waiting missions is preserved.
- A regression test injects duplicate stale entries and verifies the retry yields to all waiting missions without leaving duplicates.

## Test

```bash
pytest -q tests/unit/company/test_queue_fairness.py tests/unit/company/test_project_factory.py
```

This is in-process FIFO fairness, not a distributed scheduler or a guarantee against starvation caused by an external store or a continuously prioritizing caller.