# Persistent Project Context — AI Software Company

> Last reviewed: 2026-10-14 (UTC). This document is the handoff record for future engineering sessions. Read it before planning or changing the project. Keep it updated when architecture, priorities, milestone status, or working agreements change.

## 1. Source of truth and working agreement

- GitHub repository: https://github.com/thakareatharv49-svg/AI-Software-Company
- Default branch: `main`
- Local Windows checkout reported by the user: `C:\\Users\\TestUser123\\Documents\\Projects\\AI-Software-Company`
- GitHub is the durable engineering source of truth. Do not rely on chat memory alone; review this document, `docs/MILESTONES.md`, architecture/security docs, current code, and recent PRs before resuming.
- The user wants implementation, tests, PR creation, CI/security inspection, and merge handled directly by the assistant. **Do not tell the user to merge their own PR.**
- Work in one active implementation milestone/PR at a time. Base each branch on latest `main`; check the exact PR head SHA; inspect failures and fix the same PR rather than leaving a failed check behind.
- Merge only after all required workflows are completed successfully on the exact latest PR head: `CI`, `Secret and Credential Scan`, `Dependency Vulnerability Audit`, and `CodeQL Security Analysis`. Use squash merge with expected head SHA and verify GitHub reports `merged: true`.
- Report only what was actually implemented and verified. A merged PR or a roadmap label alone does not prove a real end-to-end capability works.

## 2. Product vision

Build a real AI-operated software company/project factory, not just a code-generation demo. The user should provide a mission; the company should plan, research, design, implement, test, repair, secure, package, publish/release under policy, observe, learn, and then continue to the next project. Human approval and safety/governance controls remain in force.

Product/branding decisions:
- The overall company and HQ system is **Nexora**; Nexora HQ tracks the company/ventures.
- The GitHub repository name stays `AI-Software-Company` to preserve links.
- The user explicitly moved away from the old “owner app” concept as the primary company tracker; Nexora is the HQ concept. Legacy owner/auth routes still exist in code and must not be mistaken for the desired product identity.
- The AI Software Company should let the user review generated product quality, ask for missing details/fixes, and approve before final GitHub publication.
- **Branding correction reported by the user on 2026-10-13:** “AI Software Developer” branding has now been fixed everywhere. Treat this as resolved unless a fresh repository-wide search or UI check finds a remaining occurrence; do not reopen it based on stale prior findings.
- Generated products should become substantial, useful applications—not only calculator, Tic-Tac-Toe, or notes demos—and the factory should eventually progress through projects continuously under configured policy.

## 3. High-level architecture/capabilities represented in the repository

The system is a Python/FastAPI application with a browser control center at `/app`. Its architecture and roadmap cover:

- Model abstraction/runtime (local Ollama is used in the user's setup), agent contracts/registry/execution, tools and permissions.
- Mission/project factory, planning, execution stages, queue/retry scheduling, progress events, task/project lifecycle.
- Durable project snapshots and durable mission jobs, audit entries, execution history, restore/recovery after cancellation/restart, and stage progress.
- Generated project workspace/materialization, isolated generated-code execution via Docker sandbox, QA/testing, security checks, review/approval and gated publication.
- Persistent organizational memory/context, research, multi-agent handoffs, learning, observability, costs/budgets, operations and reliability.
- GitHub automation and controlled artifact/repository publishing.
- Nexora HQ integration via an optional read-only aggregate status endpoint `GET /api/hq/status`, protected by a dedicated bearer token. This boundary should expose aggregate counts/status only—not mission contents or execution controls.
- Web/dashboard, customer/authentication routes, OAuth integration and legacy owner routes. Authentication/workspace integration needs end-to-end verification before calling customer access production-ready.

Useful code areas (confirm current paths before editing):
- `src/main.py`: FastAPI assembly and routers.
- `src/company/project_factory.py`: sequential factory, queue, mission lifecycle, persistence and recovery.
- `src/company/mission_jobs.py`: durable mission job model/status/transitions/recovery helpers.
- `src/company/autonomous_factory_runner.py`: autonomous runner.
- `src/company/events/events.py`: progress/event representation.
- `src/security/redaction.py`: text/value redaction.
- `src/company/control_center/`, `src/web/`, `dashboard/`: control center/web experience.
- `docs/architecture.md`, `docs/MILESTONES.md`, `docs/security.md`, `docs/security/SECURE_EXECUTION_POLICY.md`, `docs/security/SECURITY_OPERATIONS_RUNBOOK.md`: architecture, roadmap, security and incident response.

## 4. Roadmap state: two different numbering tracks

Do not conflate the permanent product roadmap milestones with the recent sequential factory-reliability/security-hardening PRs.

### Permanent roadmap (`docs/MILESTONES.md`)
- M0–M46 are marked COMPLETE in the current roadmap document, including foundation, runtime/agents/tasks, memory, project factory, engineering/QA, security/governance, recovery, operations/economics, lifecycle/reliability/red-team, and M46 company web application/productization.
- **Important qualification:** these are the current roadmap labels, not a blanket guarantee that every feature has passed live production acceptance. Validate concrete end-to-end paths and retain known gaps below.
- M47 — True One-Mission Autonomous Company: currently marked NOT STARTED. Required contract is one human mission, with the company deriving research, requirements, architecture, task graph, agent assignments, QA/security/release/deployment/monitoring plans internally rather than requiring pre-prepared execution inputs.
- M48 — Autonomous Company Operations & GitHub Control: currently marked NOT STARTED. Routine branch/commit/PR/review/merge/release/deploy/rollback operations should be automated only within enforced policy.
- M49 — Production Launch & Final Company Acceptance: currently marked NOT STARTED; final integrated acceptance gate.
- M50+ is the future continuous-evolution loop.
- Keep `docs/MILESTONES.md` authoritative for the main product roadmap. Update its statuses only when the milestone acceptance criteria are genuinely met.

### Recent factory reliability and trust-boundary hardening sequence
The recent “Milestone 1, 2, ...” PR series is a separate short-term hardening sequence, not a renumbering of the permanent M1–M49 roadmap. The following PRs are reported merged on GitHub:

| Hardening milestone | PR | Result |
|---|---:|---|
| 1 | #272 | Recover factory missions on cancellation; preserve completed stages and requeue interrupted work. |
| 2 | #273 | Preserve actionable QA evidence while redacting credentials and bounding output. |
| 3 | #274 | Protect durable factory-stage failure diagnostics from secrets/unbounded text. |
| 4 | #275 | Sanitize persisted factory worker/runner errors. |
| 5 | #276 | Show/persist execution progress for legacy runners without detailed callbacks. |
| 6 | #277 | Prevent retries from starving queued missions. |
| 7 | #278 | Protect active missions from queue cleanup. |
| 8 | #279 | Synchronize removed mission lifecycle state. |
| 9 | #280 | Reconcile durable jobs after factory restart. |
| 10 | #281 | Prevent terminal missions from reappearing after restart. |
| 11 | #282 | Reconcile stale queued snapshots against running jobs. |
| 12 | #283 | Make queued mission recovery idempotent. |
| 13 | #284 | Preserve durable progress when re-enqueueing missions. |
| 14 | #285 | Guard durable running missions against duplicate enqueue. |
| 15 | #286 | Redact recovered retry feedback before model reuse. |
| 16 | #287 | Sanitize retry feedback at use. |
| 17 | #288 | Redact manual retry feedback. |
| 18 | #289 | Redact mission revision feedback. |
| 19 | #290 | Redact legacy objective context during revision. |
| 20 | #291 | Redact mission inputs before planning. |
| 21 | #292 | Redact legacy mission data during restore. |
| 22 | #293 | Redact persisted audit messages and metadata. |
| 23 | #294 | Sanitize progress events before exposure. |
| 24 | #295 | Sanitize durable mission job messages. |
| 25 | #296 | Bound restored mission plan text. |
| 26 | #297 | Sanitize mission plans at write boundaries. |
| 27 | #298 | Bound/redact mission input text before persistence/planning. |
| 28 | #299 | Sanitize restored mission jobs at read time; rewrite unsafe legacy records. |
| 29 | #302 | Sanitize durable mission and project snapshot reads. |
| 30 | #303 | Redact and bound persistent runtime-run results and errors. |
| 31 | #304 | Redact and bound durable project-output manifests on write and read. |
| 32 | #305 | Redact and bound durable audit entries on write and legacy reads. |
| 33 | #306 | Cap durable audit-history reads and return a chronological page of newest entries. |
| 34 | #307 | Sanitize mission and plan fields before durable factory snapshot writes; clamp snapshot counters. |
| 35 | In progress | Normalize mission-job mission/plan text, diagnostics, and retry counters at the durable write boundary. |

Most recent confirmed merged PR at this review: [#307 — Milestone 34: sanitize factory snapshot writes](https://github.com/thakareatharv49-svg/AI-Software-Company/pull/307), merge commit `e84ab9c538a6f7ba66ce83cd3a053c4b9c11c433`. All required CI, secret scanning, dependency audit, and CodeQL checks passed on the exact PR head before merge. Milestone 35 is hardening durable mission-job writes.

## 5. Latest hardening details

- M31 (#304) sanitizes durable project-output manifests on writes and reconstructed reads, redacting credential-bearing repository/product URLs and bounding publication messages.
- M32 (#305) redacts and bounds durable audit entries before writes and after legacy reads, including nested metadata.
- M33 (#306) caps audit-history reads at 500 records by default and returns the newest page in chronological order.
- M34 (#307) sanitizes factory snapshot mission/plan text before writes and clamps persisted counters.
- M35 hardens the remaining durable mission-job write boundary by reusing read-time normalization for mission/plan content, redacting/bounding diagnostics, and clamping negative retry counters.

The reliability/security sequence has been strengthening the mission lifecycle and the durable-data trust boundaries:
- Cancellation, restart, retries, stale project snapshots, and durable job state are reconciled so interrupted work can resume without duplicating or resurrecting terminal work.
- Queue fairness and active-mission protections prevent one failing mission or cleanup path from starving/removing unrelated work.
- Progress, QA evidence, failure details, audit messages, retry feedback, mission inputs, plans, and durable job messages are redacted and bounded at various boundaries.
- M28 added sanitization on durable job load: mission fields, nested plan free text, and job messages are normalized immediately when read, and changed legacy records are rewritten.
- Regression tests have been added to cover the specific cases in each PR. Do not assume all other persistence/restore entry points are now covered; inspect remaining trust boundaries next.

## 6. User-reported environment and operating details

- Windows + PowerShell + VS Code.
- Local checkout path: `C:\\Users\\TestUser123\\Documents\\Projects\\AI-Software-Company`.
- Python 3.13.7 in `.venv`; Git for Windows; 12-core CPU and about 15.7 GB RAM reported previously.
- Ollama has `llama3.2:latest` installed; an earlier basic generation test succeeded.
- PostgreSQL and Docker are required for the documented durable database and container-isolated execution paths.
- README documents the default local port `8000`; the user recently used `http://127.0.0.1:8011/app` after a port conflict. Confirm the running process/port rather than assuming either port is always active.
- `LOCAL_ACCESS_ENABLED=true` was reported enabled in development settings, and is intended only for loopback development; never enable this bypass in shared/production environments.
- Do not assume the local service is currently running just because it ran in an earlier conversation.

## 7. Known issues / gaps to re-check before declaring the factory reliable

These are user-reported symptoms and open investigation items, not claims that the latest code still definitely has each bug:
1. Large missions (e.g. Notes/Expense Tracker) repeatedly became blocked; at one point every stage remained `planned`.
2. The factory queue appeared to sit for hours / queued projects did not start.
3. The user wanted a way to delete queued or blocked missions, plus less scrolling and a larger/new-mission submission area.
4. The user wants a meaningful review loop: inspect generated product, request missing features/fixes, then approve final publication.
5. **Branding:** user reports that “AI Software Developer” branding has now been fixed everywhere. The previous inconsistent-branding finding is resolved; only reopen if a fresh repository-wide search or UI check finds a regression.
6. Customer Google/GitHub sign-in and workspace creation previously encountered database/schema and missing-workspace/foreign-key errors. Re-test current migrations and full auth-to-workspace flow before claiming production-ready customer onboarding.
7. The permanent roadmap's M47–M49 one-mission autonomy and launch acceptance remain open in `docs/MILESTONES.md`.

## 8. Security and release constraints

- Generated code should run in the restricted container by default; host mode is an explicit development exception and is not OS isolation.
- Never expose real tokens or credentials in code, logs, audit messages, issue/PR text, or this document.
- Keep authorization server-side; do not trust client-supplied workspace IDs without membership/ownership checks.
- GitHub publication/release must remain gated by quality/security checks and approval of the exact artifact; changes to an approved artifact require re-approval.
- The Nexora HQ status integration is read-only and aggregate-only.
- Follow `docs/security.md`, `docs/security/SECURE_EXECUTION_POLICY.md`, and `docs/security/SECURITY_OPERATIONS_RUNBOOK.md` for detailed rules.

## 9. Recommended next work sequence

1. After this context document is merged, inspect all durable restore/read boundaries beyond `ProjectFactory._load_job` and add focused regression tests for malformed/legacy state. Keep this as one small PR and validate all four required workflows.
2. Reproduce the user's blocked/queued mission problem through the actual factory path (not just isolated unit tests); identify the earliest stage that fails to transition, and make failure/progress visible and actionable.
3. Verify the queue starts the next healthy mission after a blocked/timed-out one and preserves FIFO/fairness.
4. Verify delete/cancel controls for queued/blocked missions, including durable job, project snapshot, audit/event, and UI state consistency.
5. Continue M47 one-mission autonomy only after reliability and review gates are demonstrated; then M48, and finally M49 acceptance. Branding is no longer an active task unless regression evidence appears.

## 10. Required handoff checklist for every new session

1. Read this document and `docs/MILESTONES.md`.
2. Inspect current `main`, the last several merged PRs, and any open PRs/check failures.
3. Verify which milestone/PR is actually latest; do not trust a stale conversation summary over GitHub.
4. State the current objective briefly, implement one milestone, add regression tests, and open a PR.
5. Wait for the four required checks on the exact head SHA; inspect/fix any failure.
6. Merge only after all four pass, verify merged status, and update this context/roadmap when the durable project state materially changes.


---

## 11. Verified handoff update — 2026-10-14 (supersedes older hardening status above)

This section is the newest verified state. If older sections above conflict with this update or the live GitHub PR state, use the newest merged commits, live PR state, and current `docs/MILESTONES.md`.

### Latest factory-recovery hardening milestones

- **M67 — COMPLETE**, PR #352, merge commit `b1b3486c81ff7316a2b3c338bf1f086f794eb583`: malformed duplicate recovery snapshots cannot shadow later valid snapshots.
- **M68 — COMPLETE**, PR #353, merge commit `67812bfd74b4669906f15dc248c8b942bc5f1429`: restored snapshot counters are bounded and non-finite values normalize safely.
- **M69 — COMPLETE**, PR #354, merge commit `4cc42ebd1956a9b7ea1ba61db27ffc1397fba425`: durable mission-job attempt counters are bounded and normalized during validation/recovery.
- **M70 — COMPLETE**, PR #355, merge commit `5adcffdb599044ddef27b22474a326d35970646d`: normalized attempt counters are persisted for snapshot-backed and orphaned queued jobs; recovery skips affected items if required writes fail. All four required workflows passed on PR head `e2a98adee9a37a8c35fafdb97e497451ef6b54ec`.
- **M71 — IN PROGRESS**, PR #356: `Persist Sanitized Orphan Recovery State`. It persists sanitized mission/plan data for queued orphan jobs even when counters were already valid, and fails closed when required durable normalization cannot be saved. Current PR head before this context update was `7106e79c3b8fc439da3b0011b5585ace6df446b8`; all four required workflows passed on that exact head. Adding this context update changes the PR head, so re-check workflows on the new head before merging.

### M71 implementation and tests

- Code: `src/company/project_factory.py` — queued orphan recovery detects changes to sanitized mission/plan state as well as attempt counters, persists the normalized durable job, and skips queueing if that write fails.
- Tests: `tests/unit/company/test_factory_orphaned_job_recovery.py` — verifies legacy credential-bearing mission text is redacted in durable storage and an unsaved sanitized job is not queued.
- Roadmap: `docs/MILESTONES.md` — M70 marked COMPLETE and M71 marked IN PROGRESS in PR #356. Keep the main roadmap and this context aligned after merge.

### Immediate next actions

1. Verify PR #356's current head and all four required workflows after any new commit.
2. Inspect failed steps and fix failures on the same PR; do not merge with pending/failed required checks.
3. Merge PR #356 by squash only after CI, secret scan, dependency audit, and both CodeQL languages pass on its exact head; verify `merged: true`.
4. Update this context and roadmap to reflect the verified merge, then continue with M72 when requested.
5. Continue to treat this recovery-hardening sequence as distinct from permanent product milestones M47–M49. Those remain open until their actual end-to-end acceptance criteria pass.

### Working agreement reaffirmed

The user explicitly requires the assistant to do all PR checks, failure fixes, and merges. Never ask the user to merge. Be fast by batching status checks, but never report a merge or test success that GitHub has not verified.


---

## 12. Verified handoff update — 2026-10-14 (M71 merged; M72 active)

- **M71 — COMPLETE**, PR #356, merge commit `eaeb2030e08e424a15e7b322c62e0788b766f8ed`. The exact PR head `d34132be1a2e92c641bbabd72f31f7a9b07dca12` passed CI, Secret and Credential Scan, Dependency Vulnerability Audit, and both CodeQL language jobs before squash merge.
- M71 persists sanitized mission/plan content for queued orphan durable jobs and skips queueing when required durable normalization cannot be saved.
- **M72 — IN PROGRESS**, branch `milestone-72-fail-closed-snapshot-sanitization`: fail-closed sanitization for legacy project snapshots. It tracks whether recovery had to change sensitive mission/plan/diagnostic text or normalize counters, and will refuse to queue that snapshot if its repair cannot be persisted. Mission IDs are reserved only after the item is terminally handled or safely restored.
- M72 regression test covers a credential-bearing legacy snapshot with an oversized counter when the snapshot store refuses writes.
- Next: inspect current PR head; require all four workflows on that exact SHA, fix any failure on the same branch, merge only after all checks pass, and verify the merged result. Keep permanent product milestones M47–M49 distinct and open until end-to-end acceptance passes.


---

## 13. Verified handoff update — 2026-10-14 (M72 merged; M73 active)

- **M72 — COMPLETE**, PR #357, merge commit `d73582eaf1952a15ca7f026b4bc9be767fcb3833`. Exact head `a8231838ede0eff08b176ab34139eaba350c9d61` passed CI, Secret and Credential Scan, Dependency Vulnerability Audit, and CodeQL Security Analysis before merge.
- M72 makes restored snapshots fail closed when security/counter repairs cannot be persisted; roadmap/context status must stay aligned with the merged implementation.
- **M73 — IN PROGRESS**, branch `milestone-73-fail-closed-durable-identity-scan`: durable identity reconciliation must fail closed when the durable store's full identity scan errors. A failed scan is not an empty index; otherwise a stale project snapshot could be resurrected without proving there is no conflicting durable row.
- Regression test covers a durable identity index outage and verifies the snapshot is not queued.
- Next: verify all four required workflows on the exact M73 PR head, repair failures on the same branch, merge only after all pass, then verify merge status. Continue one implementation milestone at a time; never ask the user to merge.


---

## 14. Verified handoff update — 2026-10-14 (M73 merged; M74 active)

- **M73 — COMPLETE**, PR #358, merge commit `e5dfbee11d2ff5e41a730270dcf4976107cdc650`. The exact head `57635da4803ff739115945f1412ea4d044c72c17` passed CI, Secret and Credential Scan, Dependency Vulnerability Audit, and both CodeQL language checks before squash merge.
- M73 fails closed when durable identity enumeration throws; a failed scan is not treated as an empty index.
- **M74 — IN PROGRESS**, branch `milestone-74-fail-closed-without-identity-enumeration`: the same invariant must hold when a durable store has no `list_all()` capability. A direct lookup returning no row cannot establish absence of conflicting embedded mission IDs without enumeration.
- Regression test uses a lookup-only durable store and asserts the stale snapshot is not queued.
- Next: validate M74 on its exact latest PR head, repair any failed workflow, merge only after all required checks pass, verify the merge, and keep the roadmap/handoff synchronized. Do not conflate this reliability-hardening sequence with permanent product milestones M47–M49.


---

## 15. Verified handoff update — 2026-10-14 (M74 merged; M75 active)

- **M74 — COMPLETE**, PR #359, merge commit `e38ee143d3a7b0fd919e2d526571fdd58bdc29ba`. User confirmed merge at 2026-10-14T20:32:44Z. M74 prevents stale snapshot recovery when a durable store does not implement full identity enumeration.
- **M75 — IN PROGRESS**, branch `milestone-75-fail-closed-on-malformed-identity-index`: fail closed when an enumerated durable identity index contains unreadable or empty identities. Ignoring malformed rows could let an old snapshot be treated as orphaned without proving the durable index is conflict-free.
- Regression coverage verifies a malformed durable row causes the affected snapshot to be skipped.
- Next: run the full CI, secret scan, dependency audit, and both CodeQL language checks on the exact latest PR head; fix any failures, merge only when all required checks pass, verify merge, and synchronize this handoff. Keep permanent product milestones M47–M49 open until their real end-to-end acceptance criteria pass.

### Working agreement

The user expects autonomous milestone execution, including code review, CI repair, required security checks, merging, and persistent roadmap updates. Never ask the user to merge. Work on one implementation milestone at a time and verify every merge.


---

## 16. Verified handoff update — 2026-10-14 (M75 merged; M76 active)

- **M75 — COMPLETE**, PR #360, merge commit `54e08597241cafa4acac4ed4a4b5306ef6c8ceb0`. All required checks passed on exact head `364be1b56a2430d37daf97303aac6f2d1653dca4`: CI, Secret and Credential Scan, Dependency Vulnerability Audit, and CodeQL Python plus JavaScript/TypeScript.
- M75 fails closed when durable identity enumeration contains unreadable or empty identity records, rather than silently treating the index as conflict-free.
- **M76 — IN PROGRESS**, branch `milestone-76-bidirectional-durable-identity-reconciliation`: enforce both sides of the durable key/embedded mission identity mapping. A row whose durable key equals the snapshot ID but embeds another mission must block recovery even if direct lookup returns no row.
- Regression test simulates a corrupt indexed row hidden by direct lookup and verifies the snapshot is not queued.
- Next: validate the exact PR head through CI, secret scan, dependency audit, and both CodeQL language jobs; fix failures, merge only after all checks pass, verify the merge, and keep roadmap/handoff aligned. Product milestones M47–M49 remain open pending true end-to-end acceptance.



---

## 17. Verified handoff update — 2026-10-14 (M76 merged; M77 active)

- **M76 — COMPLETE**, PR #361, merge commit `b98e6f5cec823478e914c444b7a30c6b7c3dce1b`. CI, secret scan, dependency audit, and both CodeQL language checks passed on exact head `eafaea5c1da7007a008a26f3544576ba7b2fdc96`.
- M76 validates durable key and embedded mission ID symmetrically, preventing a corrupt key-to-mission mapping from allowing stale snapshot resurrection when direct lookup misses it.
- **M77 — IN PROGRESS**, branch `milestone-77-reject-duplicate-durable-identities`: reject ambiguous durable identity indexes containing duplicate durable keys or duplicate embedded mission IDs.
- Regression test covers duplicate durable keys in the enumerated index. Continue to run all required workflows on the exact PR head and merge only when all pass; verify merge status and keep permanent product milestones M47–M49 open until true end-to-end acceptance.
