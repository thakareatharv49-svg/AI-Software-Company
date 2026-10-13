# Persistent Project Context — AI Software Company

> Last reviewed: 2026-10-13 (UTC). This document is the handoff record for future engineering sessions. Read it before planning or changing the project. Keep it updated when architecture, priorities, milestone status, or working agreements change.

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
| 28 | #299 | Sanitize restored mission jobs at read time; rewrite unsafe legacy records. |\n| 29 | #302 | Sanitize durable mission and project snapshot reads. |\n| 30 | #303 | Redact and bound persistent runtime-run results and errors. |

Most recent confirmed merged PR at this review: [#303 — Milestone 30: sanitize persistent runtime run records](https://github.com/thakareatharv49-svg/AI-Software-Company/pull/303), merge commit `a2c17d1407ac9cb6b40a3ff2881bee34b97e067c`. The four required workflows passed on the PR head before merge. Milestone 31 continues the persistence trust-boundary work by sanitizing durable project-output manifests.

## 5. Latest hardening details

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
