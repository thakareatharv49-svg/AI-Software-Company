# Nexora / AI Software Company — Revised Improvement Plan

> Research review: 2026-10-15  
> Status: Proposed execution plan; milestones become complete only after implementation and verification.  
> Source of truth: this plan defines strategic sequencing; `docs/MILESTONES.md` tracks individual acceptance criteria and status.

## North-star outcome

Turn the current factory into a dependable software-production system: accept a substantial mission, research and plan it, build it in a restricted environment, prove it works, show the user a reviewable product, publish only an approved and verified artifact, observe it in operation, learn from outcomes, and then move to the next mission.

The near-term bottleneck is not adding more agents. It is proving that the existing mission lifecycle is reliable end to end. The recent M67–M81 sequence has hardened durable recovery identity checks, but unit-level persistence correctness alone does not prove a large mission can run from submission to usable product and approval.

## Research basis

This plan incorporates the following primary guidance reviewed on 2026-10-15:

- **OWASP GenAI Security Project / LLM Top 10 (2026):** treat prompt injection, excessive agency, unsafe tool use, sensitive-data exposure, and unbounded consumption as design risks, not merely prompt-writing problems. <https://genai.owasp.org/> and <https://owasp.github.io/www-project-top-10-for-large-language-model-applications/>
- **NIST AI Risk Management Framework and Generative AI Profile:** govern, map, measure, and manage risks throughout design, evaluation, deployment, and operation. <https://www.nist.gov/itl/ai-risk-management-framework> and <https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence>
- **GitHub Actions supply-chain security:** protect workflow permissions, use OIDC instead of long-lived cloud credentials where applicable, and use artifact attestations for releasable binaries/images when the release pipeline supports them. Attestations provide provenance; they do not themselves prove an artifact is safe. <https://docs.github.com/en/actions/how-tos/secure-your-work> and <https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations>
- **Current repository evidence:** the durable recovery hardening from M67 onward repeatedly found trust-boundary edge cases. The persistent handoff also records previously reported blocked/queued large missions, the need for visible failure reasons, a product review/revision/approval loop, and customer OAuth/workspace setup errors. These remain verification targets until reproduced and closed by real-path tests.

## Guiding rules

1. **Real-path evidence beats isolated success.** A unit test is necessary but not sufficient for user-visible capabilities.
2. **Fail closed on uncertain state, fail visibly to the operator.** Do not silently drop, resurrect, duplicate, or indefinitely queue work.
3. **Bound every autonomous loop.** Explicit time, token, retry, tool-call, concurrency, disk, and cost budgets with cancellation and backpressure.
4. **Least privilege by default.** Agents receive only the tools, repository scope, credentials, and network access required for the current task.
5. **Separate generated claims from verified evidence.** A model saying “tests passed” is not evidence; capture process exit status, test reports, artifact hashes, and reproducible logs.
6. **Human approval attaches to an exact artifact.** Any code or dependency change after approval invalidates that approval.
7. **Make recovery idempotent.** Replaying a job, webhook, or release step must not duplicate side effects.
8. **Measure before optimizing.** Capture stage latency, retry causes, queue wait, cost, failure rates, and QA defects before setting performance targets.
9. **Prefer small, reversible changes.** Each implementation milestone should have focused regressions, migration/rollback considerations, and exact-head CI/security verification.
10. **Keep free/local-first paths viable.** Provider-specific capabilities should be optional behind interfaces; no paid service should be required for basic local development unless documented.

## Prioritized execution sequence

### Track A — Mission lifecycle reliability (P0, do first)

**A1. Defensive snapshot decoding and recovery boundaries**
- Validate snapshot container shape, mission/plan object shape, enums, timestamps, counters, and required fields before dereferencing or constructing runtime models.
- Make each corrupt record independently skippable; one bad snapshot must not abort recovery of healthy records.
- Distinguish “no record”, “corrupt record”, “storage unavailable”, and “write-back failed” in structured diagnostics.
- Preserve the fail-closed durable identity invariants established by M67–M81.
- Tests: null/wrong-type snapshot, missing nested mission, malformed plan, unknown status, throwing properties/iterators, read/write exceptions, mixed corrupt and healthy records, repeated restore idempotency.

**A2. Real end-to-end mission lifecycle test harness**
- Exercise the same public submission → planning → queue → worker → generated files → QA → review state transitions used by the app.
- Add deterministic fake model/provider and fake GitHub adapters; reserve a smaller opt-in integration test for the actual local model/runtime.
- Test a realistic multi-stage app mission, not only tiny demo missions.
- Persist a machine-readable stage trace and attach artifacts/log references to test failures.

**A3. Queue liveness and fairness**
- Define and test queue invariants: each accepted mission is queued/running/terminal, active work is bounded, one blocked job cannot starve healthy work, and cancellation releases resources.
- Add stale-worker leases/heartbeats, bounded retries with jitter, deadlines, stuck-stage detection, and safe recovery after process restart.
- Expose queue age, last progress, current stage, next retry, blocker, and actionable remediation in HQ.
- Verify FIFO/fairness policy and explicitly document any priority override.

**A4. Durable state and concurrency correctness**
- Use atomic state transitions/compare-and-swap or transactions where supported; document consistency guarantees where storage backends differ.
- Add idempotency keys for mission creation, stage execution, GitHub operations, and publication.
- Test concurrent enqueue/cancel/retry/revise/restore operations and duplicate delivery.
- Test storage outages, partial writes, schema-version migrations, and rollback.

**Exit gate for Track A:** an end-to-end multi-stage mission reliably reaches a terminal state or a visible, actionable blocked state; restart/replay does not duplicate or resurrect work; a failed mission does not prevent the next healthy mission from progressing.

### Track B — Product quality and user acceptance (P0/P1)

**B1. Evidence-based QA gate**
- Require format/lint, unit tests, integration tests, type checks where applicable, dependency/security checks, and build/startup smoke tests appropriate to the generated stack.
- For web apps, launch the generated app in an isolated browser and test critical user journeys, navigation, forms, responsive layouts, console errors, and server errors.
- Capture test reports, screenshots, browser traces, logs, and artifact hashes as structured evidence.
- Separate mandatory gates from optional advisory checks; a skipped check must never be reported as passed.

**B2. Independent reviewer and defect loop**
- Have a reviewer agent assess the implementation against the original mission and acceptance criteria, independently of the builder's self-evaluation.
- Convert findings into severity-ranked defects with reproduction steps and file/line references.
- Permit bounded fix-and-retest cycles; prevent the builder from closing its own unresolved critical findings without fresh test evidence.
- Detect repeated no-op retries and escalate with a concise blocker report.

**B3. Product preview → revise → approve → publish**
- Give users a stable preview link or local preview, generated feature checklist, known limitations, and QA evidence.
- Support revision requests while preserving mission history and linking each revision to the exact commit/artifact.
- Require explicit user approval before production publication for customer-facing products.
- Bind approval to a commit SHA and artifact digest; any subsequent change requires new approval.
- Test cancel, reject, request-changes, re-review, and approval revocation.

**Exit gate for Track B:** users can inspect the actual generated product, request changes, see evidence that those changes were tested, and approve the exact artifact that gets published.

### Track C — AI and execution security (P1, ongoing)

**C1. Tool authorization and prompt-injection containment**
- Treat repository files, issues, web pages, generated code, test output, and model responses as untrusted data.
- Enforce tool authorization in code, not in system prompts alone. Use allowlists, argument schemas, path/repository scoping, and deny-by-default for destructive operations.
- Require approval for high-impact actions such as production deployment, credential/permission changes, destructive data operations, and publishing to public destinations.
- Add adversarial tests for malicious README/issue content, instruction smuggling, secret exfiltration attempts, path traversal, shell injection, and cross-workspace access.

**C2. Sandbox hardening**
- Keep generated code in isolated containers by default; verify resource, filesystem, process, network, and privilege restrictions.
- Make host execution an explicit development-only exception and impossible to enable accidentally in shared/production settings.
- Add egress policy, CPU/memory/time/disk limits, process cleanup, non-root execution, and secrets isolation.
- Threat-model the container runtime and any browser automation boundary.

**C3. Secrets, tenant isolation, and audit**
- Keep credentials out of prompts, generated files, logs, telemetry, and durable mission text; use scoped short-lived credentials where feasible.
- Verify workspace membership/ownership on every server-side read/write, not just at login.
- Add cross-tenant isolation tests for projects, missions, artifacts, logs, GitHub connections, and preview links.
- Make audit records append-only where practical, redact sensitive fields, bound payloads, and record actor, action, target, result, and correlation ID.

**C4. Model and dependency risk controls**
- Pin and review critical workflow actions/dependencies; use lockfiles, vulnerability scans, SBOMs for releases where supported, and update policies.
- Track model/provider version, prompt/template version, tool policy version, and evaluation suite version for each run.
- Evaluate prompt injection, unsafe output handling, sensitive data disclosure, excessive agency, and unbounded consumption as regression suites.

**Exit gate for Track C:** no agent can obtain more privilege than the configured policy grants; destructive/public actions are approval-gated; tenant-boundary and adversarial tests are part of CI.

### Track D — Customer onboarding and operator experience (P1)

- Verify Google/GitHub OAuth from callback through identity persistence, workspace creation, membership assignment, session refresh, logout, and revocation using clean databases and migrations.
- Make workspace creation and membership assignment transactional/idempotent to avoid the previously observed missing-workspace foreign-key failures.
- Separate customer-facing product access from Nexora operator/admin access with explicit roles and server-side checks.
- Add a demo path that uses isolated sample data and cannot reach real customer data or production credentials.
- Redesign HQ mission status to reduce scrolling and prominently show new mission entry, current stage, queue health, last progress, blockers, and available actions.
- Ensure queued/blocked mission delete/cancel actions reconcile in-memory queue, durable job, snapshot, audit/event history, and UI state.

**Exit gate for Track D:** fresh-database auth tests and browser-level onboarding pass; customers cannot access HQ-only controls or another workspace; operator UI exposes actionable lifecycle state without requiring log spelunking.

### Track E — Observability, economics, and continuous operation (P1/P2)

- Add correlation IDs from mission through agent/tool/stage, storage, GitHub PR, QA, and publication.
- Track queue wait, stage duration, retry count, token/provider usage where available, estimated cost, sandbox utilization, QA pass rate, escape defects, and cancellation rate.
- Provide budget caps per mission/project/workspace, global concurrency limits, timeouts, and alerts before hard limits are reached.
- Add health/readiness checks, structured logs, metrics, trace/event timelines, and redaction tests.
- Add evaluation datasets and regression scoring for planning quality, requirement coverage, code correctness, tool policy adherence, user acceptance, and cost/latency.
- Only enable autonomous next-project scheduling when prior mission terminal state, budget availability, and approval/release rules are satisfied.

**Exit gate for Track E:** operators can explain what happened, why it failed, how much it cost, and whether the next mission may safely start.

### Track F — Release integrity and maintenance (P2)

- Build from a clean, pinned environment; record source commit, dependency lock state, test results, artifact digest, and release metadata.
- Add signed/provenance-backed release artifacts where the release channel supports GitHub artifact attestations; verify attestations rather than merely generating them.
- Publish an SBOM for releasable products when practical and document dependency/license review.
- Make releases reproducible enough to compare output hashes where the toolchain permits.
- Define rollback/disable procedures, migration safety, backup/restore drills, vulnerability response, and incident runbooks.
- After publication, monitor crash/error signals and dependency alerts; route verified issues back into a human-reviewed maintenance mission.

**Exit gate for Track F:** every release can be traced to source and test evidence, rollback is documented and rehearsed, and post-release maintenance is bounded and auditable.

## First implementation milestones to schedule

These are planned, not complete. Keep each implementation in its own focused PR and update `docs/MILESTONES.md` as work starts and finishes.

1. **M82 — Defensive Snapshot Record Decoding:** safely validate record and nested-object shapes before recovery dereferences; skip corrupt records without losing healthy records.
2. **M83 — Mixed-Record Restore Isolation:** prove one malformed record, storage exception, or write-back failure cannot abort or poison unrelated healthy restore candidates.
3. **M84 — Real-Path Mission Lifecycle Harness (COMPLETE):** deterministic public HTTP submission and factory execution with the real generated-product pipeline, executed pytest QA, independent review, durable output manifest, audit history, and structured failure trace; exact-head CI/security checks passed and PR #372 was merged.
4. **M85 — Queue Liveness and Stuck-Stage Diagnostics (COMPLETE):** bounded heartbeat thresholds tied to execution deadlines, explicit liveness metadata, and actionable queued/running/blocked diagnoses.
5. **M86 — Idempotent Lifecycle Operations:** cover duplicate submission, retry, cancellation, revision, restart, and concurrent operations.
6. **M87 — Generated Product QA Evidence:** run build/startup smoke tests and browser critical-path checks for supported web products.
7. **M88 — Independent Review and Approval Binding:** enforce review findings and approval tied to exact source/artifact identity.
8. **M89 — Tool Policy and Adversarial Safety Tests:** test untrusted repository content, tool boundaries, destructive-action approval, and sandbox limits.
9. **M90 — Customer Auth/Workspace End-to-End Acceptance:** prove OAuth, workspace membership, tenant isolation, and HQ/customer separation on a fresh database.
10. **M91 — Mission Observability and Budget Enforcement:** structured event timeline, cost/resource ceilings, and bounded autonomous scheduling.
11. **M92 — Release Provenance and Rollback Readiness:** verifiable artifact provenance, SBOM where feasible, and rehearsed rollback.
12. **M93 — Continuous Improvement Evaluation Loop:** curated evaluations and regression gates based on measured quality, safety, latency, and cost.

After M93, re-evaluate priorities from real telemetry and user acceptance rather than extending the milestone number without evidence.

## Milestone definition of done

Every milestone must include:
- Focused tests for expected behavior, edge cases, and failure paths.
- A test through the real application path when the feature is user-visible or lifecycle-related.
- Explicit security and privacy implications, including tenant isolation and untrusted input where relevant.
- Clear operational signals for success, failure, retries, and recovery.
- Documentation and persistent context updated in the same PR.
- All required CI, secret scanning, dependency audit, and CodeQL checks passing on the exact PR head before merge.
- A verified merge SHA and accurate status update; do not infer success from a PR being opened or a model-generated report.

## Review cadence

Review this plan after each major track exit gate, after any production incident, and when user-reported failures contradict the current architecture. Keep the plan ambitious but evidence-driven: the goal is a useful software company, not a large count of merged milestones.
