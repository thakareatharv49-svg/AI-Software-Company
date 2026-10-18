# R7: safe mission resumption

Manual retry resumes from the last valid completed stage rather than replaying the entire mission.

## Resume contract

- Completed stages remain completed when all declared prerequisites remain completed.
- Failed and interrupted (`running`) stages return to `planned`, with stale failure details cleared.
- If a completed stage depends on a stage that must be rerun, it is invalidated and returned to `planned`; this invalidation propagates through downstream completed stages.
- Independent completed work remains intact.
- Attempt counters are preserved so retry history is not erased.
- The stored plan is copied before recovery, avoiding mutation of the prior durable checkpoint.

This improves retry efficiency while preserving dependency correctness. It does not treat a failed stage as successful, and downstream stages cannot retain a completed state when their prerequisites are no longer verified.

## Regression tests

```powershell
python -m pytest tests/unit/company/test_mission_jobs.py -q
python -m pytest tests/unit/company/test_factory_recovery_persistence.py tests/unit/company/test_factory_cancellation_recovery.py -q
```
