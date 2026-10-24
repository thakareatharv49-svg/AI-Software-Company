# M89 — Executable Dependency-Aware Task Graph

## Waterfall phase

Detailed design and implementation increment. This milestone strengthens the engineering-task dependency boundary; it does not claim end-to-end task checkpoint/resume is complete.

## Contract

- Every engineering task has a stable, non-empty unique ID.
- Every dependency must reference an existing task.
- Self-dependencies and cycles are invalid.
- The scheduler order is deterministic and dependency-first.
- A task is ready only when it is still planned and all prerequisites have status `completed`.
- Invalid graphs are rejected before agent execution starts.
- Legacy plans with no engineering-task list remain loadable and do not fail this new preflight.

## Current implementation

The mission execution pipeline validates the engineering graph before registering or invoking agents. The execution request receives tasks in validated dependency-first order and an explicit `ready_engineering_task_ids` list. Tests cover ordering, ready filtering, duplicate IDs, missing dependencies, self-dependencies, and cycles.

## Remaining acceptance work

This increment does not yet provide individually executed engineering tasks or durable task-transition checkpoints. Those are required before M89 can be marked complete:

1. Execute each task as a separate bounded worker unit.
2. Persist `running/completed/failed` task transitions alongside the mission plan/job.
3. On restore, normalize interrupted task states without resetting verified completed tasks.
4. Prove through the real factory worker that downstream tasks stay blocked until dependencies complete, and that restart resumes safely.
5. Run targeted tests, full CI/security checks, and a deterministic interruption/recovery integration test.

## Safety invariant

No model-reported success or generated file may substitute for a persisted, verified task completion state. Failed or interrupted prerequisites must keep descendants blocked.
