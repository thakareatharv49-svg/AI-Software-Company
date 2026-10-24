# M87 — Mission Requirements and Acceptance Contract

Status: IN PROGRESS.

## Purpose

Turn each mission into a versioned, reviewable contract before implementation. The contract is persisted on the mission plan so retries and serialized plans retain the requirements that generated the engineering tasks.

## Contract fields

- schema_version: contract format version.
- mission_id, mission_name, objective: identity and source mission.
- functional_requirements: stable requirement IDs, original statement, source, and a corresponding acceptance-check prompt.
- constraints: deduplicated, non-empty user-supplied constraints.
- acceptance_criteria: functional statements plus explicit constraints.
- status and open_questions: indicate whether the objective is sufficiently concrete for planning.

The first version intentionally uses deterministic parsing rather than inventing a product specification with an LLM. It splits the supplied objective into distinct statements and keeps each statement traceable. Acceptance-check text is a review/test prompt, not proof that a requirement passed.

## Clarification behavior

A request consisting only of a generic product noun (for example, “Build an app”) is marked needs_clarification. validate_mission_plan reports the open question so callers can stop before implementation and ask the user to specify target users, core workflows, required capabilities, and testable success conditions.

This is conservative ambiguity detection, not a general contradiction solver. Complex conflicting requirements and richer user-story extraction remain follow-up work. No requirement is marked implemented or verified by this contract alone.

## Compatibility and verification

MissionPlan.requirements_contract is optional when loading older persisted plans. New plans built by build_mission_plan receive a contract automatically. Validation checks contract/plan mission identity, objective consistency, requirements presence, and clarification status.

Run focused tests:

    python -m pytest tests/unit/company/test_m87_requirements_contract.py -q

M87 is not complete until required CI passes and the contract behavior is verified through the running factory path. The M86 real-factory benchmark gate remains outstanding independently.
