# R16 — Execution Timeline Observability

## Purpose

Make stalled or failed missions diagnosable from persisted operational evidence rather than a single last-error string.

## Progress breadcrumbs

Whenever the factory persists plan progress, it appends a `MISSION_PROGRESS_SNAPSHOT` audit entry containing the attempt number, stages executed, each stage's name/status/attempt count and bounded diagnostic detail, plus QA and security status. The existing audit redaction boundary is applied to timeline details.

These are append-only breadcrumbs, not a replacement for the authoritative mission plan/job record. They show the last state that was observed and persisted before later execution changes or failures.

## Final decision summary

The final factory audit entry now summarizes stage counts, a stage-by-stage timeline, engineering-task status counts, QA status/exit code/duration, security status, execution mode, attempt count, and the terminal decision (`completed`, `retry_queued`, `blocked`, `paused`, or `other`).

## Validation

`tests/unit/company/test_execution_timeline.py` verifies stage snapshots and redaction of sensitive stage details. Full CI and security workflows must pass before this change is considered validated.
