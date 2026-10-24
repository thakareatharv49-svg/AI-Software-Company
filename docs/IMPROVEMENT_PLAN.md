# Nexora / AI Software Company — Revised Improvement Plan

> Research and repository-state review: 2026-10-24  
> Status: Proposed execution plan; milestones become complete only after implementation and verification.  
> Source of truth: this plan defines strategic sequencing; `docs/MILESTONES.md` tracks individual acceptance criteria and status.

## North-star outcome

Turn the current factory into a dependable software-production system: accept a substantial mission, research and plan it, build it in a restricted environment, prove it works, show the user a reviewable product, publish only an approved and verified artifact, observe it in operation, learn from outcomes, and then move to the next mission.

The near-term bottleneck is not adding more agents. It is proving that the existing mission lifecycle can reliably deliver a useful, multi-file product end to end. The M82–M85 work addressed lifecycle/restore isolation and queue liveness, but unit-level persistence correctness alone does not prove that distinct web, API, and CLI missions can be built, executed, repaired, reviewed, and released with evidence.

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

## Current implementation program: M86–M97

The authoritative sequence is in `docs/MILESTONES.md`. This section must stay aligned with it; do not maintain a second, conflicting M86–M93 schedule. All items below are planned unless the master roadmap explicitly records an evidence-backed status.

1. **M86 — Large-Project Benchmark and Baseline (IN PROGRESS):** define distinct web/API/CLI benchmark cases and capture reproducible real-factory results with stage/check evidence, duration, retries, and command outputs. The initial fixture catalog and contract tests are in PR #421; the real benchmark runner and first measured baseline are still required.
2. **M87 — Mission Requirements and Acceptance Contract:** persist user-visible requirements, non-goals, deliverables, and evidence-linked acceptance criteria.
3. **M88 — Architecture and Project-Type Planning:** choose compatible stacks from mission requirements and environment capabilities; persist architecture and toolchain decisions.
4. **M89 — Executable Dependency-Aware Task Graph:** enforce prerequisites in the actual worker path, including cycle/missing-dependency rejection and restart safety.
5. **M90 — Multi-File Implementation and Incremental Resume:** verify cross-module coherence and resume safely without duplicate or contradictory output.
6. **M91 — Project Bootstrap and Runtime Compatibility:** generate project manifests/configuration, check runtimes early, and report unsupported capabilities precisely.
7. **M92 — Real Build and Test Execution:** run bounded sandbox commands and preserve actual exit-code/test evidence.
8. **M93 — Application-Level Acceptance Testing:** validate real API/database/browser/user flows; process health alone is not product acceptance.
9. **M94 — Evidence-Driven Repair Loop:** convert failures into bounded repair tasks, classify retryability, and re-run regressions.
10. **M95 — Product Quality Review and Revision:** capture objective and subjective findings, require verified fixes, and prevent self-approval over failed gates.
11. **M96 — Release Readiness and Artifact Integrity:** bind approval to the exact tested artifact/revision and block unsafe or unverified publication.
12. **M97 — Continuous Multi-Mission Delivery Soak Test:** measure fairness, progress, failure/recovery, isolation, and safe progression through multiple missions.

After M97, reprioritize using benchmark results, actual factory telemetry, and user acceptance—not milestone count alone.

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


## Lifecycle phase gates

This project uses the Waterfall + Incremental hybrid model. Waterfall governs lifecycle approval gates; Incremental delivery divides approved work into small, testable, dependency-ordered slices. Apply these gates to the M86–M97 program and future work:

1. **Requirements exit:** scope, non-goals, constraints, risks, and measurable acceptance criteria are documented.
2. **Design exit:** architecture/interfaces, data contracts, stack/toolchain assumptions, security boundaries, and verification plan are reviewed.
3. **Implementation exit:** planned deliverables are present, code review is complete, and focused tests cover expected and failure paths.
4. **Verification exit:** real application/factory-path tests and required security workflows pass; acceptance criteria link to evidence; unresolved blockers are explicit.
5. **Release exit:** the candidate artifact matches the tested revision and required human approval is recorded.
6. **Maintenance/change exit:** defect/change impact is documented and regression verification is complete.

If a gate fails, return to the earliest phase affected by the evidence, correct the issue, and repeat downstream gates that the change impacts. Do not silently skip a phase or mark a phase complete based on documentation alone.


## Combined Waterfall + Incremental execution

Waterfall phase gates control approval; incremental slices control implementation size. First review requirements and measurable acceptance criteria, then approve the design and verification plan. Split approved work into dependency-ordered increments, each with focused implementation, tests, and regression checks. At each phase gate, verify all required increment and end-to-end acceptance evidence. A passing increment is not proof that its parent milestone or phase is complete. If verification fails, correct the affected design/implementation and rerun impacted checks. Merge only with required checks green on the exact PR head; release only the exact tested revision with required approval. Apply this policy to M86–M97.
