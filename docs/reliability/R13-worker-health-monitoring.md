# R13 — Worker Health Monitoring and Stuck-Job Detection

## What changed

- Factory projects now track the UTC time an attempt starts, the latest persisted progress heartbeat, and the number of progress updates during the attempt.
- `ProjectFactory.worker_health()` provides a read-only diagnostic snapshot with `idle`, `waiting`, `healthy`, or `stale` status, mission identity, heartbeat age, threshold, and an operator-facing diagnostic.
- Each persisted plan-progress update refreshes the heartbeat before writing the project snapshot.
- The default stale threshold follows the configured execution timeout, so a legitimate long model/provider call is not flagged before its normal timeout. Callers can supply a stricter positive threshold for monitoring.
- A stale signal never automatically cancels, retries, or requeues the mission. This avoids duplicate execution when the worker may still be inside a long provider call.

## How to use

Call `factory.worker_health()` to inspect the current worker, or `factory.worker_health(stale_after_seconds=120)` to apply a 120-second monitoring threshold. Treat `stale` as an alert for log inspection and controlled recovery, not proof that the process is dead.

## Safety and limitations

- Health snapshots are diagnostic and do not provide distributed locking or cross-process ownership.
- A worker inside a long operation that does not emit progress may appear stale under an intentionally short custom threshold.
- The heartbeat is persisted with the factory project snapshot; health is based on the current process's active-project reference.
- Automatic lease expiry and takeover are intentionally excluded until the system can prove that the previous executor no longer owns the mission.

## Tests

`tests/unit/company/test_worker_health.py` covers idle and active states, recent and stale heartbeats, the timeout-based default threshold, and invalid threshold values.
