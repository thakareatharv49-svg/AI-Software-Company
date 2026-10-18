# R14 — Timeout and Cancellation Safety

## Problem

Execution timeout and application cancellation can interrupt a project while one or more stages are in flight. Recovery must preserve completed stages, clear interrupted stages, and avoid scheduling a second in-process attempt if durable state could not be reconciled.

## Changes

- Cancellation now resets only in-flight stages using the existing recovery helper and attempts to persist the resumable snapshot and durable mission-job transition before placing the mission back in the in-process queue.
- If either recovery write fails, the factory withholds automatic in-process retry, logs the persistence failure, and records an explicit diagnostic. This is intentionally conservative: the operator may need to restart the worker so durable RUNNING state can be reconciled by startup recovery.
- Cancellation continues to propagate as asyncio.CancelledError; shutdown/caller cancellation is not silently converted into success.
- A regression test simulates a project snapshot store outage during cancellation and verifies the mission is not put back into the live queue.
- Existing timeout handling remains bounded by execution_timeout_seconds; timeout failures are recorded as failed execution evidence and flow through the factory retry/failure policy.

## Safety behavior

A timeout or cancellation does not prove that an external provider or subprocess stopped immediately. The factory therefore does not start a concurrent replacement execution as part of cancellation cleanup. Stale durable state is reconciled through the established restart-recovery path rather than speculative in-process takeover.

## Tests

tests/unit/company/test_factory_cancellation_recovery.py covers normal cancellation resume and recovery-persistence failure.
