# R18 — Controlled Recovery Actions

## Goal

Turn recovery guidance into explicit, guarded operations without allowing a diagnostic recommendation to trigger execution by itself.

## API

ProjectFactory.recover_mission(mission_id, action) supports:

- `inspect`: read durable mission status and recommend a next action without mutating mission state.
- `resume`: rehydrate a mission only when the durable job is already `QUEUED`. It writes the project snapshot before adding the project to the in-memory queue.
- `retry`: delegate to the existing manual retry path only when durable status is `FAILED` or `BLOCKED`.

## Safety guarantees

- Unknown actions are rejected.
- Missing durable jobs raise `KeyError`.
- A running factory worker blocks resume/retry actions.
- A running, completed, or cancelled job cannot be rehydrated by the resume action.
- An already-queued mission is not duplicated.
- If snapshot persistence fails, the mission is not added to the in-memory queue.
- Recovery is explicit; no action runs automatically based on diagnostics.

This is an in-process guard. It does not provide distributed locking across multiple factory processes; deployments with multiple workers must continue to enforce single-writer ownership at the durable store/worker layer.

## Tests

Unit tests cover idempotent resume, durable status validation, persistence failure, read-only inspection, invalid actions, and active-worker protection.
