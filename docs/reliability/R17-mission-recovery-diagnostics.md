# R17 — Mission Recovery Diagnostics

## Goal

Turn the mission's last known state into an actionable recovery summary without automatically restarting work when execution safety is uncertain.

## Diagnostic fields

Each final factory outcome audit includes `recovery_diagnostics`:
- normalized mission status, bounded attempt count, and current queue depth;
- the first failed stage, otherwise the first running stage, otherwise the first planned stage;
- bounded stage detail and last-error summary;
- a conservative recommended action and an explicit `safe_to_retry_automatically` flag.

## Recovery guidance

Completed missions need no action. Blocked/failed missions require inspection and an explicit retry decision. Cancelled missions require checking the persisted recovery state. A running stage recommends checking worker heartbeat before restarting, avoiding duplicate execution. A queued mission with remaining work can resume from a safe stage.

The diagnostic is advisory: it does not itself retry, cancel, or mutate mission state. The existing lifecycle and persistence safeguards remain authoritative.

## Privacy and validation

Stage detail and error summaries are bounded here and pass through the existing audit redaction boundary when persisted. Unit tests cover action selection, blocking-stage identification, conservative handling of running/blocked missions, and bounded values.
