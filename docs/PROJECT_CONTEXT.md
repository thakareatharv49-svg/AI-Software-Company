# Persistent Project Context — AI Software Company

> Last reviewed: 2026-10-24 (UTC). This is the durable engineering handoff. Re-check live GitHub state before relying on branch, PR, or CI details.

## 1. Repository and working agreement

- Repository: https://github.com/thakareatharv49-svg/AI-Software-Company
- Default branch: `main`; latest verified main commit at this review: `4bdc9634aec5a56bc417c08cd8c77b31dcc66536` (merged planning PR #420).
- Local checkout reported by the user: `C:\\Users\\TestUser123\\Documents\\Projects\\AI-Software-Company`.
- GitHub is the durable engineering source of truth. Read this file, `docs/MILESTONES.md`, relevant architecture/security docs, current code, and recent PRs before resuming.
- The user expects the assistant to inspect the implementation, make changes in GitHub, add tests, inspect CI/security results, fix failures, open PRs, and handle merges where appropriate. Do not ask the user to merge their own PR.
- Work one implementation milestone at a time from the latest verified main. Avoid broad rewrites or duplicate subsystems when a focused change will solve the issue.
- Merge only after all required checks succeed on the exact latest PR head: CI, Secret and Credential Scan, Dependency Vulnerability Audit, and CodeQL Security Analysis. Use expected-head SHA and verify GitHub confirms the merge.
- The user has also asked to accumulate batches of PRs at times. Before merging unrelated open PRs, inspect current PR state and preserve an explicit batch-hold instruction if it is still in force.
- A merged PR, green isolated test, roadmap label, or generated files alone do not prove an end-to-end capability works. Report only verified outcomes.

## 2. Product goal and identity

Build a real autonomous AI software company/project factory, not a code-generation demo. Given one human mission, the company should plan, research, design, implement, validate, repair, secure, review, package, and release software under explicit governance. It should be able to recover from interruption and move to the next eligible mission without hiding failures.

Branding and product decisions:
- Company/HQ identity: **Nexora**.
- Repository name remains **AI-Software-Company** to preserve existing links.
- Generated products should be substantial, coherent, multi-file applications—not repetitive calculator, Tic-Tac-Toe, or generic notes demos.
- The user expects to inspect a generated product, request missing features/fixes, and approve before final external GitHub publication.
- The dashboard should use AI Software Company/Nexora branding consistently. A previous “AI Software Developer” branding issue was reported fixed; reopen only if a fresh search or UI check finds a regression.
- Human approval and safety gates must remain in force for external publication and other irreversible actions.

## 3. Architecture map

The application is Python/FastAPI with a browser control center at `/app`. Major areas include:

- Model runtime and local Ollama integration; agent contracts, registry, execution, tools, and permissions.
- Mission planning/controller, project generation, multi-file checkpoints, factory queue/worker, retries, cancellation, durable mission jobs, and recovery.
- Generated artifact/workspace validation, restricted execution/sandbox, QA/test command execution, security review, product review, and gated publication.
- Persistent memory, audit/event history, costs/budgets, operational diagnostics, and dashboard APIs.
- GitHub automation and Nexora's optional read-only aggregate HQ status endpoint. Do not expose mission contents or execution controls through aggregate status.
- Customer/authentication/OAuth/workspace routes and legacy owner routes. Customer onboarding is not production-ready until migrations, workspace membership, authorization, and OAuth flows pass an end-to-end test.

Useful paths to verify before edits:
- `src/main.py` — FastAPI assembly and routers.
- `src/company/project_factory.py`, `src/company/autonomous_factory_runner.py`, `src/company/mission_jobs.py` — factory execution and durable lifecycle.
- `src/company/mission_controller/` — mission plan models, planner, execution, and failure policy.
- `src/company/project_generator.py`, `src/company/artifact_validation.py` — generated products and artifact checks.
- `tests/integration/`, `tests/unit/company/`, `tests/fixtures/` — real-path integration coverage, regression tests, and fixtures.
- `docs/MILESTONES.md` — authoritative milestone roadmap; `docs/IMPROVEMENT_PLAN.md` — improvement program; `docs/security.md` and `docs/security/` — security policy/runbooks.

## 4. Current roadmap and next major problem

The master roadmap contains milestones through M85, followed by the new large-project delivery program M86–M97. Do not rely on stale M47–M49 or old hardening tables from earlier handoff notes; read the current `docs/MILESTONES.md` for exact statuses.

### Large-project delivery program — M86–M97

The core unresolved problem is reliable end-to-end delivery of useful multi-file products, including proof that they run and satisfy the mission. PR #420, “Plan M86–M97: Large-project delivery program,” was merged on 2026-10-24 as commit `4bdc9634aec5a56bc417c08cd8c77b31dcc66536`. CI, secret scan, dependency audit, and CodeQL all reported success on its exact head SHA before merge. The PR changed planning documentation only; it did not change runtime behavior.

Milestones, to be implemented sequentially:
- **M86 — Benchmark baseline:** reproducible cases, machine-readable results, exact stage/check failures.
- **M87 — Requirements contract:** persist requirements, non-goals, deliverables, and evidence-linked acceptance criteria.
- **M88 — Architecture/project-type planning:** select compatible stacks and define boundaries before implementation.
- **M89 — Executable dependency graph:** enforce prerequisite ordering and persist graph state.
- **M90 — Multi-file implementation/resume:** validate cross-file coherence and safely resume interrupted work.
- **M91 — Bootstrap/runtime compatibility:** manifests, toolchain checks, capability adapters, actionable blockers.
- **M92 — Real build/test execution:** bounded sandbox commands and exit-code-backed evidence.
- **M93 — Application-level acceptance:** verify actual routes, persistence, user flows, and runtime behavior.
- **M94 — Evidence-driven repair:** bounded, classified repair attempts and regression checks.
- **M95 — Product quality review/revision:** close findings and prevent self-approval over failed gates.
- **M96 — Release readiness/integrity:** ensure the approved revision is the exact tested revision.
- **M97 — Multi-mission soak test:** verify queue fairness, recovery, isolation, and evidence-backed outcomes.

### Active implementation slice at this review: M86

Branch: `m86-large-project-benchmark-baseline`; [PR #421](https://github.com/thakareatharv49-svg/AI-Software-Company/pull/421) is open and awaiting exact-head CI/security results.

Changes currently prepared on that branch:
- `tests/fixtures/large_project_benchmark_cases.json` defines three distinct project cases: a persistent browser app, an API-backed service, and a CLI utility.
- `tests/unit/company/test_large_project_benchmark_contract.py` validates catalog structure, distinct project types, safe expected paths, complete test contracts, and precise artifact-validator failure diagnostics.
- `docs/MILESTONES.md` marks M86 IN PROGRESS and explicitly states that the catalog is not proof of benchmark success.
- `docs/IMPROVEMENT_PLAN.md` has been aligned to the same M86–M97 sequence to remove the older conflicting M86–M93 schedule.

M86 is **not complete**. The next implementation task is a real benchmark runner that runs each fixture through the actual factory path, records per-stage/per-check status, command evidence, duration and retries, and preserves the first baseline. Keep provider-dependent model calls opt-in; default CI must be deterministic and credential-free. Do not mark a case passed solely because its catalog is valid.

## 5. Known risks and symptoms to re-validate

These were reported or investigated earlier and are not assertions that each bug still exists:
1. Large missions (such as Notes/Expense Tracker) could remain blocked with stages still planned.
2. Queued missions could appear to wait indefinitely or fail to start.
3. The user requested clear deletion/cancellation for queued or blocked missions and a less cumbersome mission-composer UI.
4. Product review must allow requested revisions before approval/publication.
5. Google/GitHub OAuth and workspace setup previously encountered missing-table and missing-workspace/foreign-key failures. Verify current migrations and the complete login-to-workspace path before claiming onboarding is production-ready.
6. The factory must not confuse “files generated” or “process alive” with product acceptance; use real command and application-level evidence.
7. Verify that failures, retries, cancellation, restart, and one mission's persistence error do not starve or corrupt other queued missions.

## 6. Environment notes

- User development environment: Windows + PowerShell + VS Code.
- Python 3.13.7 in `.venv`; local Ollama model `llama3.2:latest` was previously available.
- PostgreSQL and Docker are needed for the documented durable database and container-isolated execution paths.
- The default local port was documented as 8000; 8011 was used during a port conflict. Check the active process/port rather than assuming either.
- `LOCAL_ACCESS_ENABLED=true` was previously reported in development settings and must never be used as a shared/production auth bypass.
- Do not assume the local application is running based on prior sessions.

## 7. Security and release constraints

- Run generated code in the restricted sandbox by default; host execution is a development exception, not OS isolation.
- Never commit or disclose real credentials in code, generated artifacts, logs, audit messages, issues/PRs, or this context file.
- Enforce workspace membership and ownership server-side; do not trust client-supplied workspace IDs.
- Keep generated artifact paths scoped to the mission workspace and validate them before writing or release.
- External publication/release must be gated by quality/security checks and approval of the exact artifact revision. A changed revision requires renewed review.
- Nexora HQ status integration should remain read-only and aggregate-only.

## 8. Working sequence

1. Check latest main, relevant open PRs, and current workflow results.
2. Inspect existing implementation and reuse it; work one milestone per PR.
3. Add focused unit tests and real factory-path integration tests.
4. Run relevant tests, full CI, secret scan, dependency audit, and CodeQL; fix failures in the same PR.
5. Merge only after all required checks pass on the exact latest PR head, unless an explicit batch-hold instruction still applies.
6. Verify the merge SHA and update milestone/context documents based on evidence.
7. Never claim a milestone complete until its stated acceptance criteria are met on the real factory path.


## 9. Mandatory development methodology — Waterfall + Incremental

The user has selected a **Waterfall + Incremental hybrid model**. Waterfall governs lifecycle order and phase gates; Incremental development delivers approved scope in small, testable additions. Apply both rules to new development and roadmap execution.

Ordered phases:
1. Requirements analysis — scope, use cases, non-goals, constraints, and testable acceptance criteria.
2. System/detail design — architecture, data contracts, interfaces, project-type decisions, threat boundaries, and test plan.
3. Implementation — approved design delivered in focused milestones.
4. Verification/validation — automated and real-path tests, security checks, product acceptance, and traceable evidence.
5. Deployment/release — package the exact tested revision and require appropriate approval before external publication.
6. Maintenance — controlled defect fixes and change requests with impact analysis and regression verification.

Phase-gate policy:
- Record requirements and design decisions in GitHub before implementation begins for that scope.
- A milestone cannot pass its gate on code generation, a successful process start, or a model's own assertion alone; use reproducible test evidence.
- Defects found in verification go back to the relevant implementation/design step, then the affected tests are rerun.
- Keep the master roadmap, improvement plan, and project context consistent.
- No phase/milestone is marked complete while required CI/security checks are pending or failing, critical defects are open, or acceptance evidence is absent.
- Every PR should identify the Waterfall phase and increment, approved requirement/design references, acceptance criteria, tests, known limitations, and relevant phase-exit evidence.
- External publication remains subject to user approval of the exact tested revision.


## Development methodology: Waterfall + Incremental

The selected approach is a hybrid model. Waterfall controls lifecycle order and approval gates: requirements, design, implementation, verification/validation, release, and maintenance. Incremental development controls delivery within approved scope: small, coherent, dependency-ordered capabilities, each with requirement/design references, measurable acceptance criteria, focused tests, regression checks, risks, and limitations. A passing increment does not complete its parent milestone or phase. Defects return to the affected design/implementation step and impacted tests must rerun. Required CI/security checks must pass on the exact PR head before merge. External release requires approval of the exact tested revision. M86–M97 remain sequential milestone gates; increments cannot bypass their criteria.
