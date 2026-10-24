# M88 — Architecture and Project-Type Planning

Status: IN PROGRESS.

## Purpose

Before implementation starts, turn a mission into a persisted architecture decision that is specific enough to guide repository creation and verification. Project type must follow mission evidence, and the chosen stack must be checked against an explicit capability profile.

## Implemented in this increment

- Added versioned architecture-plan and dependency models plus a RuntimeCapabilities profile.
- Added deterministic selection for browser apps, API services, CLI utilities, Python libraries, full-stack web apps, and a conservative general Python application.
- Recorded rationale, runtime/language/framework, repository layout, component boundaries, interfaces, data-model guidance, and validation strategy.
- Added dependency/tool preflight against the supplied capability profile. Missing required language, framework/runtime, or test tooling is reported as an unsupported capability instead of silently assumed to exist.
- Attached architecture plans to new mission plans and added structural/identity checks.
- Kept the architecture plan optional so legacy persisted plans without the field remain loadable.
- Sanitized architecture fields during durable mission restoration.

## Capability profile contract

RuntimeCapabilities represents the configured execution environment, not automatic host discovery. Callers that know the actual worker/sandbox capabilities must pass that profile. The default profile is a documented local-development baseline only; it is not proof that a particular machine or container has those tools installed. This planner does not install dependencies or execute generated code.

## Validation

Run focused tests:

    python -m pytest tests/unit/company/test_m88_architecture_planning.py -q

Coverage includes project-type selection, distinct layouts and interfaces, missing capability blockers, persisted plans, identity mismatch, and legacy plan compatibility.

## Acceptance gate

M88 remains IN PROGRESS until required CI/security checks pass on the exact PR head and representative missions are exercised through the running factory path. This increment does not complete M86's real-factory benchmark or M87's real-path requirements-contract gate.
