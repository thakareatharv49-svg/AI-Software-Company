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

The mission execution pipeline validates the engineering DAG before agent work begins. During the execution stage it chooses only a currently ready task, executes that task as a bounded agent request, and checkpoints each `running/completed/failed` transition through the factory progress callback. The next task is not eligible until every prerequisite is `completed`.

A failed task stops the execution stage and leaves its descendants planned. Restore recovery converts interrupted `running` tasks back to planned and invalidates stale completed descendants whose prerequisites are no longer complete. Manual retry resets failed/in-flight tasks while retaining valid completed prerequisites. Task attempts and bounded diagnostic details are stored on the mission plan.

## Remaining acceptance work

1. Run the targeted tests and full CI/security suite on the exact PR head.
2. Exercise a representative mission through the real factory worker, not just the pipeline unit fixture.
3. Verify durable-store checkpoint writes and a simulated interruption/restart against the configured factory store.
4. Confirm QA blocks delivery when task work is incomplete or acceptance evidence fails.

## Safety invariant

No model-reported success or generated file may substitute for a persisted, verified task completion state. Failed or interrupted prerequisites must keep descendants blocked.
