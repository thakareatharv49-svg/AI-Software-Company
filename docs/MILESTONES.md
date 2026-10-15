# AI Software Company — Master Milestone Roadmap

## Purpose

This file is the permanent source of truth for the AI Software Company.

The destination is **not** a collection of demos or GitHub-only modules. The destination is a real software company that can receive one human mission, autonomously turn it into software, operate that software, learn from it, and continue to the next project within human-defined safety and governance boundaries.

GitHub is the engineering source of truth. The company itself must operate through its own runtime and control plane.

## Completion Rule

A milestone is COMPLETE only when:

1. Implementation is finished.
2. Tests are added.
3. Ruff passes.
4. Full test suite passes.
5. `git diff --check` passes.
6. Changes are committed.
7. Changes are pushed to `origin/main`.
8. Working tree is clean.
9. Milestone status is explicitly marked COMPLETE.
10. Where applicable, the capability is exercised through the real company path, not only through isolated unit tests.

Never mark a milestone complete merely because files were added or a PR was merged.

---

# Completed Foundation

## M0 — Foundation & Planning
Status: COMPLETE

Vision, architecture, lifecycle, engineering rules and permanent roadmap.

## M1 — Engineering Foundation
Status: COMPLETE

Repository, Python environment, testing and linting foundation.

## M2 — AI Runtime
Status: COMPLETE

Initial AI runtime.

## M3 — Agent Engine
Status: COMPLETE

Agent models, registry and execution engine.

## M4 — Task Engine
Status: COMPLETE

Task lifecycle and state management.

## M5 — Master Manager
Status: COMPLETE

Company-level coordination foundation.

## M6 — Project Engine
Status: COMPLETE

Project lifecycle and management.

## M7 — Engineering Agents
Status: COMPLETE

Engineering-agent foundation.

## M8 — Sandbox
Status: COMPLETE

Sandboxed execution foundation.

## M9 — QA & Autonomous Debugging
Status: COMPLETE

Testing and autonomous debugging foundation.

## M10 — Security & Code Review
Status: COMPLETE

Security and review foundation.

## M11 — GitHub Automation
Status: COMPLETE

GitHub integration and repository automation foundation.

## M12 — Memory & Learning
Status: COMPLETE

Initial memory and learning architecture.

## M13 — Dashboard
Status: COMPLETE

Dashboard foundation.

## M14 — Continuous Autonomous Company
Status: COMPLETE

Continuous-company architecture foundation.

## M15 — Core Autonomous Company Integration
Status: COMPLETE

Core pipeline integration across runtime, tools, sandbox, persistence, GitHub, QA, memory, dashboard and security.

## M16 — Production Runtime & Prevention Infrastructure
Status: COMPLETE

Production runtime, lifecycle, monitoring, supervision, shutdown, metrics, alerting, backpressure, resource enforcement, timeout, recovery, persistence, observability and prevention infrastructure.

---

# AI Company Expansion

## M17 — Memory Integration
Status: COMPLETE

Connect persistent memory to real company execution.

Scope:
- Agent, task, project and mission memory
- Decision and failure memory
- Execution and QA memory
- Context retrieval before execution
- Memory writing after execution
- Handoff and restart context
- Cross-agent context

Goal:
The company does not lose important context between executions.

## M18 — Real AI Model Layer
Status: COMPLETE

Production model abstraction, provider routing, structured output, streaming, retries, context limits, model health and fallback behavior.

Goal:
Agents use real AI models through a stable internal interface.

## M19 — AI CEO / Master Manager
Status: COMPLETE

Mission interpretation, goal decomposition, planning, assignment, resource decisions, monitoring, failure handling and human escalation.

Goal:
A human mission becomes executable company work.

## M20 — Universal Tool System
Status: COMPLETE

Filesystem, terminal, Git, GitHub, web research, HTTP/API, database, Python, testing, package management, permissions, logging, timeout and resource controls.

Goal:
Agents can safely interact with real development environments.

## M21 — Real Project Factory
Status: COMPLETE

Project discovery, requirements, product definition, architecture, repository initialization, task generation and project lifecycle.

Goal:
The company can start real software projects.

## M22 — Autonomous Engineering
Status: COMPLETE

Code generation/modification, dependencies, branches, commits, pull requests, review, refactoring, documentation and builds.

Goal:
Agents can implement software tasks.

## M23 — Autonomous QA & Debugging 2.0
Status: COMPLETE

Test generation, failure analysis, root-cause detection, automatic repair, regression testing, quality scoring and release gates.

Goal:
The company can find and fix its own failures.

## M24 — Production Security & Governance
Status: COMPLETE

Permissions, capabilities, tool allowlists, secret protection, isolation, sandbox policies, repository protection, approval gates and audit trails.

Goal:
Autonomous does not mean unrestricted.

## M25 — Self-Healing & Recovery
Status: COMPLETE

Runtime, agent, task and project recovery, checkpointing, diagnosis, retry strategies and escalation.

Goal:
The company can recover without losing work.

## M26 — Production Memory & Knowledge Engine
Status: COMPLETE

Persistent organizational knowledge, retrieval, consolidation, ranking and durable context.

Goal:
The company develops institutional memory.

## M27 — Agent Registry & Agent Marketplace
Status: COMPLETE

Agent capabilities, versions, health, specialization, selection and composition.

Goal:
The company can select suitable agents dynamically.

## M28 — Artifact & Document System
Status: COMPLETE

Specifications, architecture, research, QA reports, decisions, project documentation, release notes and versioned artifacts.

Goal:
Important company knowledge is durable.

## M29 — Project State & Control Plane
Status: COMPLETE

Authoritative company, project, task, agent, runtime, dependency, release and recovery state.

Goal:
The company always knows what is happening and what happens next.

## M30 — Human Control Center
Status: COMPLETE

Mission submission, monitoring, logs, memory, costs, security alerts, approvals, pause/resume, stop and override foundations.

Goal:
Humans remain in control while the company operates autonomously.

## M31 — AI Execution Coordinator
Status: COMPLETE

Company-level AI execution coordination and persistent execution history.

## M32 — Real-World Research Engine
Status: COMPLETE

Real research providers, source validation and research reports.

## M33 — Multi-Agent Collaboration
Status: COMPLETE

Agent communication, handoffs, shared context and dependency coordination.

## M34 — Company Dashboard
Status: COMPLETE

Company-wide dashboard data boundary covering projects, agents, tasks, runtime, memory, QA, security, costs, deployments, failures, research, metrics and audit.

## M35 — Continuous Learning Engine
Status: COMPLETE

Failure/success analysis, agent performance, strategy evaluation, process optimization and knowledge consolidation.

## M36 — End-to-End Autonomous Project
Status: COMPLETE

Integrated path:

MISSION
→ AI CEO
→ RESEARCH
→ RESEARCH HANDOFF
→ PRODUCT DEFINITION
→ ARCHITECTURE
→ ENGINEERING
→ QA
→ DEBUGGING
→ SECURITY
→ GITHUB
→ DEPLOYMENT
→ MONITORING
→ LEARNING
→ DASHBOARD

Important limitation discovered:
M36 proves a real end-to-end orchestration path, but its current request contract still contains externally prepared project/task inputs. Therefore it is not yet the final one-mission autonomy contract. That gap is intentionally addressed later rather than hidden.

---

# Acceptance & Production Controls

## M37 — Autonomous Software Company Acceptance
Status: COMPLETE

Formal acceptance checks for the autonomous company.

Scope:
- Real mission
- Real project
- Real repository
- Real agents
- Real AI execution
- Real tools
- Real coding
- Real QA
- Real debugging
- Real GitHub
- Real memory
- Real deployment
- Failure recovery
- Security validation
- Human override
- Complete audit trail

Additional final requirement:
- Verify the one-human-mission contract is not bypassed by pre-supplied planning data.

Goal:
Prove that the system behaves as an autonomous software company.

## M38 — Billing, Cost & Budget Control
Status: COMPLETE

Scope:
- Model/API costs
- Token usage
- Infrastructure costs
- Project budgets
- Agent spending limits
- Cost forecasting
- Budget alerts
- Automatic spending controls
- Human approval for expensive operations

Goal:
Operate economically and prevent uncontrolled spending.

## M39 — Compliance, Privacy & Data Governance
Status: COMPLETE

Scope:
- Data classification
- PII detection
- Sensitive-data handling
- Retention
- Deletion/export controls
- Audit
- Repository isolation
- Dependency/license governance

Goal:
Operate safely with real-world data and software.

## M40 — Evaluation & Benchmarking
Status: COMPLETE

Scope:
- Agent benchmarks
- Coding benchmarks
- QA benchmarks
- Research benchmarks
- Regression benchmarks
- Model/agent comparison
- Autonomous-run scoring
- Quality history

Goal:
Measure whether the company is actually improving.

---

# Final Company Buildout

## Post-Merge Validation

M36-M45 validation fixes are tracked through CI before final completion.

## M41 — Scalability & Distributed Execution
Status: COMPLETE

Turn the company from a single-machine execution system into a scalable software factory.

Scope:
- Worker abstraction
- Multiple execution workers
- Distributed task queues
- Concurrent task execution
- Concurrent project execution
- Scheduling
- Resource allocation
- Worker health
- Worker registration
- Fault-tolerant coordination
- Backpressure across workers
- Retry and reassignment
- Persistent distributed state
- Safe concurrency limits
- Local development mode
- Production distributed mode

Goal:
The company can safely scale beyond one execution process without losing authoritative state or safety controls.

Acceptance:
Run multiple independent workloads concurrently and prove correct task ownership, recovery and state consistency.

---

## M42 — Company Operations & Economics
Status: COMPLETE

Turn technical execution into company-level decision making.

Scope:
- Project prioritization
- Opportunity scoring
- Project cost estimation
- Revenue estimation
- ROI estimation
- Portfolio management
- Resource allocation
- Agent allocation
- Project continuation decisions
- Project abandonment decisions
- Budget-aware planning
- Economic risk analysis
- Company-level objectives
- Strategic decision records

Goal:
The AI company can decide **what it should build and operate**, not merely how to execute assigned tasks.

Acceptance:
Given multiple candidate opportunities and finite resources, the company produces a justified portfolio decision and executes according to that decision.

---

## M43 — Autonomous Product Lifecycle
Status: COMPLETE

Close the loop after the first deployment.

Lifecycle:

BUILD
→ DEPLOY
→ MONITOR
→ OBSERVE
→ RECEIVE FEEDBACK
→ DETECT BUGS / FEATURES
→ RESEARCH
→ PRIORITIZE
→ PLAN
→ IMPLEMENT
→ TEST
→ SECURITY
→ DEPLOY
→ MONITOR
→ LEARN

Scope:
- Product feedback ingestion
- User/operational feedback
- Bug discovery
- Feature discovery
- Product analytics
- Backlog generation
- Automatic prioritization
- Product roadmap evolution
- Autonomous maintenance
- Safe release gates
- Versioning
- Rollback
- Product memory

Goal:
A product does not stop at its first release. The company continuously operates and improves it.

Acceptance:
A deployed product generates a maintenance/feature signal, and the company autonomously takes it through planning, implementation, validation and release.

---

## M44 — Production Reliability / SRE
Status: COMPLETE

Make the company capable of operating real production systems reliably.

Scope:
- Monitoring
- Alerting
- Incident management
- Structured logs
- Metrics
- Distributed tracing
- Health checks
- SLI/SLO/SLA definitions
- Error budgets
- Backups
- Disaster recovery
- Rollbacks
- Capacity management
- Incident diagnosis
- Automated remediation
- Post-incident learning
- Reliability reports

Goal:
Autonomous software remains reliable after deployment.

Acceptance:
Inject controlled production failures and prove detection, diagnosis, recovery, rollback where appropriate, auditability and learning.

---

## M45 — Final Security & Red-Team Validation
Status: COMPLETE

Attempt to break the autonomous company before trusting it with real-world operation.

Scope:
- Prompt injection
- Tool abuse
- Secret leakage
- Sandbox escape
- Permission escalation
- Malicious repositories
- Dependency attacks
- Agent manipulation
- Data exfiltration
- Supply-chain attacks
- Unsafe autonomous GitHub actions
- Unsafe deployment actions
- Cross-project data leakage
- Governance bypass
- Cost-control bypass
- Recovery abuse
- Adversarial task inputs

Goal:
Demonstrate that the company remains inside its security, governance and human-control boundaries under adversarial conditions.

Acceptance:
All critical findings are fixed or explicitly blocked by policy, and the red-team suite passes without unsafe autonomous behavior.

---

# Productization Milestones

These milestones are intentionally added because the original M41–M45 roadmap described the company engine but did not explicitly define the complete user-facing product or the final one-mission operating contract.

## M46 — Company Web Application & Productization
Status: COMPLETE

Build the actual application through which a human operates the AI Software Company.

Scope:

### Mission
- Mission submission
- Mission history
- Mission status
- Mission approval/result
- Mission cancellation

### Company
- Company overview
- Current company state
- Active projects
- Completed projects
- Company health

### Projects
- Project list
- Project details
- Project lifecycle
- Releases
- Deployments
- Product feedback

### Agents
- Agent registry
- Agent status
- Current work
- Capabilities
- Performance
- Health

### Execution
- Task graph
- Live task status
- Agent handoffs
- Execution logs
- Failure/recovery events
- QA results
- Security results

### Operations
- Costs
- Budgets
- Resource usage
- Incidents
- Alerts
- Governance findings

### GitHub
- Repository
- Branches
- Commits
- Pull requests
- Reviews
- Merge status
- Release status

### Human control
- Pause
- Resume
- Stop
- Override
- Approval requests
- Emergency shutdown

### UI architecture
- Production web frontend
- Authenticated backend/API
- Real-time execution updates
- Persistent company state
- Responsive desktop interface
- Clean production UX

Goal:
Turn the company engine into an actual application that a human can open and operate.

Acceptance:
A user can submit one mission through the web application and observe the complete company lifecycle from the UI.

---

## M47 — True One-Mission Autonomous Company
Status: NOT STARTED

Remove the architectural dependency on human-prepared execution inputs.

The required external input becomes:

**ONE MISSION**

The company itself must derive:

- Research questions
- Product requirements
- Acceptance criteria
- Architecture
- Technology choices
- Project definition
- Task graph
- Agent assignments
- QA strategy
- Security strategy
- GitHub workflow
- Deployment plan
- Monitoring plan
- Learning plan

The existing M36 `AutonomousProjectRequest` contract must be replaced or wrapped by a higher-level mission controller that can derive all downstream inputs internally.

Goal:
The human does not manually tell the company how to execute the mission.

Acceptance:
A test provides only a mission and permitted company configuration. The company derives and executes the remaining workflow without manually supplied research/task/project plans.

---

## M48 — Autonomous Company Operations & GitHub Control
Status: NOT STARTED

Remove unnecessary human operational intervention from the company loop.

Scope:
- Autonomous branch creation
- Autonomous commits
- Autonomous PR creation
- Automated review gates
- Automated merge decision within policy
- Protected production boundaries
- Autonomous release management
- Autonomous deployment triggering
- Autonomous rollback
- Autonomous issue creation
- Autonomous project state updates
- Human escalation only when policy requires it

Important principle:
The company must not be able to bypass its safety and governance controls merely because it can operate GitHub autonomously.

Goal:
The human gives the mission; the company performs its own software operations.

Acceptance:
Run a complete mission where no human manually creates branches, commits, PRs, merges, deploys or advances routine execution stages, while all policy and audit requirements remain enforced.

---

## M49 — Production Launch & Final Company Acceptance
Status: NOT STARTED

Final integrated launch gate.

Scope:
- Complete web application
- Complete backend/company engine
- One-mission autonomy
- Autonomous GitHub operations
- Autonomous product lifecycle
- Distributed execution
- Cost controls
- Governance
- Evaluation
- Reliability
- Security/red-team results
- Backup/recovery
- Observability
- Documentation
- Operational runbooks
- Deployment
- Final end-to-end mission

Final acceptance test:

YOU
→ ONE MISSION
→ COMPANY
→ RESEARCH
→ PRODUCT
→ ARCHITECTURE
→ TASKS
→ AGENTS
→ ENGINEERING
→ QA
→ DEBUGGING
→ SECURITY
→ GITHUB
→ DEPLOYMENT
→ MONITORING
→ FEEDBACK
→ IMPROVEMENT
→ NEXT WORK

No routine human orchestration between these stages.

Goal:
Prove that the project has become the actual AI Software Company we originally intended to build.

---

# M50+ — Continuous Autonomous Evolution
Status: FUTURE

After M49, the company enters continuous evolution rather than a fixed final feature list.

Scope:
- Continuous project discovery
- Continuous learning
- Agent evolution
- Workflow evolution
- Tool evolution
- Infrastructure evolution
- Self-evaluation
- Self-optimization
- Portfolio evolution
- New product discovery
- Cost optimization
- Reliability optimization
- Security improvement
- Capability expansion

Core loop:

MISSION
→ BUILD
→ DEPLOY
→ OPERATE
→ LEARN
→ IMPROVE
→ DISCOVER NEXT OPPORTUNITY
→ BUILD NEXT
→ REPEAT

The company continuously evolves while remaining within human-defined safety, governance, budget and control boundaries.

---

# Destination

The project is COMPLETE as a product when M49 passes.

The long-term company is then represented by M50+.

The final product is not merely:

- a Python package,
- a collection of agents,
- a GitHub repository,
- a dashboard,
- or a workflow demo.

It is a real AI-operated software company with:

1. A human-facing web application.
2. A company execution engine.
3. One-mission autonomous planning.
4. Autonomous engineering.
5. Autonomous QA and debugging.
6. Autonomous security controls.
7. Autonomous GitHub operations.
8. Autonomous deployment and monitoring.
9. Autonomous product evolution.
10. Persistent company memory and learning.
11. Cost and governance controls.
12. Production reliability.
13. Red-team validation.
14. Human override and emergency control.

The human provides direction.

The company performs the work.

---

# Operational Recovery Follow-on Milestones

These reliability milestones extend the operational factory beyond the original M50+ continuous-evolution outline.

## M62 — Recovery Persistence Reliability
Status: COMPLETE

- Isolate project-snapshot and durable-job persistence failures per recovery item.
- Keep terminal durable jobs out of the active queue even when stale-snapshot cleanup fails.
- Prevent duplicate queue entries from duplicate legacy snapshots.
- Add regression coverage for recovery write failures and terminal-job cleanup failures.

Acceptance: one snapshot's persistence failure does not stop unrelated recoveries, and terminal durable lifecycle state is never resurrected into active work.

## M63 — Durable Job Reconciliation
Status: COMPLETE

- Recover queued durable jobs whose project snapshot was not written before a crash.
- Recover interrupted running jobs from the durable job store and reset in-flight stages before re-queueing.
- Continue recovery from durable jobs when the project snapshot store is unavailable.
- Never re-enqueue terminal jobs; make repeated restore calls idempotent.
- Add regression tests for orphaned queued/running jobs, terminal states, store outages, and repeated restore.

Acceptance: the durable job store can recover eligible missions even when project snapshots are missing, without duplicating queue entries or resurrecting terminal work.

## M64 — Durable Job Identity & Eligibility Validation
Status: COMPLETE

- Require durable job IDs to match their embedded mission IDs before recovery.
- Admit only explicitly queued or interrupted-running jobs into the active queue.
- Fail closed on unknown/corrupt lifecycle states instead of treating them as runnable.
- Add regression tests for mismatched identities and unknown statuses.

Acceptance: malformed durable records cannot create duplicate or incorrectly eligible queue entries, and valid queued/running recovery continues unchanged.

## M65 — Snapshot & Durable Lifecycle Consistency
Status: COMPLETE

- Apply durable identity and lifecycle validation to snapshot-backed recovery as well as orphan recovery.
- Reject snapshots when the corresponding durable job has a mismatched identity or invalid lifecycle status.
- Ensure corrupt durable records cannot bypass fail-closed recovery checks through a legacy project snapshot.
- Add regression coverage for snapshot/job identity and status mismatches.

Acceptance: both recovery paths enforce the same durable identity and lifecycle invariants; malformed durable state cannot be resurrected by an older project snapshot.

## M66 — Snapshot Lifecycle Eligibility & Durable Precedence
Status: COMPLETE

- Restore a project snapshot without a durable job only when its status is explicitly queued or interrupted-running.
- Reject terminal and unknown snapshot lifecycle values instead of adding them to the active queue.
- Treat a validated durable queued status as authoritative over stale snapshot status.
- Add regression tests for terminal/unknown snapshots and durable-versus-snapshot status conflicts.

Acceptance: restored queue entries always have an eligible lifecycle state, and valid durable lifecycle state wins over stale project snapshot metadata.


## M67 — Recovery Snapshot Deduplication Safety
Status: COMPLETE

- Reserve snapshot mission IDs only after snapshot data and durable lifecycle metadata pass validation.
- Ensure a malformed earlier duplicate cannot shadow a later valid snapshot for the same mission.
- Keep duplicate prevention in place once a snapshot has passed validation, including when persistence later fails.
- Add a regression test for malformed-then-valid duplicate snapshots.

Acceptance: invalid snapshot entries cannot suppress recoverable valid work, while each mission is restored at most once per recovery pass.


## M68 — Bounded Snapshot Recovery Counters
Status: COMPLETE

- Clamp restored attempt and stage counters to a documented defensive ceiling.
- Normalize non-finite or invalid counter values to zero.
- Prevent corrupted legacy snapshots from bypassing retry budgets or polluting progress metrics.
- Add regression tests for oversized integers and non-finite values.

Acceptance: restored snapshot counters are finite, non-negative, and bounded before scheduling or dashboard use.

---

# Milestone Execution Rule

Work on exactly one active implementation milestone at a time.

Planning may span multiple future milestones, but implementation must have one active milestone.

After completing a milestone:

1. Run the complete validation gates.
2. Update this file.
3. Mark the milestone COMPLETE.
4. Commit.
5. Push to `origin/main`.
6. Verify the working tree is clean.
7. Only then begin the next milestone.

Never rely on chat history alone for the roadmap.

GitHub repository + this file are the persistent roadmap source of truth.


## M69 — Bounded Durable Job Attempt Counters
Status: COMPLETE

- Apply the same defensive attempt ceiling to durable mission jobs as to project snapshots.
- Normalize invalid, negative, non-finite, and oversized attempts before durable recovery can schedule work.
- Re-check counters during recovery so legacy objects that bypass model validation cannot restore unbounded attempts.
- Add regression coverage for oversized and non-finite durable attempt counters.

Acceptance: snapshot-backed and orphaned durable-job recovery enforce a consistent finite, non-negative, bounded attempt count.


## M70 — Persist Normalized Durable Recovery State
Status: COMPLETE

- Persist normalized attempt counters back to durable queued jobs during recovery instead of only correcting in-memory copies.
- Apply the same persistence rule to snapshot-backed and orphaned queued jobs.
- Fail closed for the affected recovery item if normalization cannot be durably saved.
- Add regression tests proving corrupt durable counters are repaired in storage.

Acceptance: once recovery accepts a queued durable job, its persisted attempt counter is finite, non-negative, bounded, and consistent with the normalized recovery state.



## M71 — Persist Sanitized Orphan Recovery State
Status: COMPLETE

- Persist sanitized mission and plan content for queued orphan jobs, even when their attempt counters were already valid.
- Keep recovery fail-closed when changed durable state cannot be saved.
- Add regression tests for credential redaction persistence and failed durable writes.

Acceptance: a recovered queued orphan cannot retain unsafe legacy mission or plan text in durable storage, and is not scheduled if required normalization cannot be persisted.


## M72 — Fail-Closed Sanitization of Restored Snapshots
Status: COMPLETE

- Track when legacy project snapshots require sensitive-text redaction or counter normalization.
- Do not enqueue a repaired snapshot when its required durable write fails.
- Reserve mission IDs only after recovery succeeds, so an unsaved unsafe duplicate cannot shadow a later valid snapshot.
- Add regression coverage for credential-bearing snapshots and failed snapshot writes.

Acceptance: recovery never schedules a snapshot whose required security/counter repair could not be persisted, while a failed unsafe duplicate does not suppress a later valid record.


## M73 — Fail-Closed Durable Identity Reconciliation
Status: COMPLETE

- Treat an unavailable durable-job identity scan as an inability to verify snapshot identity, not as an empty durable index.
- Skip snapshot recovery when the durable store's full identity scan fails, avoiding unsafe resurrection from stale snapshots.
- Add regression coverage for temporary durable-index failures.
- Keep the recovery path resilient: unrelated valid recovery items continue to be processed independently.

Acceptance: when a durable job store exists but identity reconciliation fails, snapshots are not treated as orphaned standalone truth; recovery fails closed for the affected snapshot and continues safely.


## M74 — Fail Closed Without Durable Identity Enumeration
Status: COMPLETE

- Require a durable job store to support full identity enumeration before treating a missing direct lookup as proof that a snapshot is orphaned.
- Skip snapshot recovery when identity enumeration is unsupported, just as when enumeration fails.
- Add regression coverage for lookup-only durable stores.
- Keep independent recovery items isolated so one unverifiable snapshot does not stop unrelated work.

Acceptance: a legacy snapshot is never scheduled when the configured durable job store cannot prove that no conflicting durable identity exists.


## M75 — Fail Closed on Malformed Durable Identity Index
Status: COMPLETE

- Treat unreadable durable rows as an unverifiable identity index rather than silently ignoring them.
- Reject empty durable or embedded mission identities during snapshot reconciliation.
- Skip the affected snapshot when the full identity index contains a malformed row, because absence of a conflict cannot be established safely.
- Add regression coverage for an enumerated durable row with no readable mission identity.

Acceptance: snapshot recovery proceeds only when every enumerated durable row has a readable, non-empty durable ID and embedded mission ID; malformed identity data cannot be mistaken for proof that a snapshot is orphaned.


## M76 — Bidirectional Durable Identity Reconciliation
Status: COMPLETE

- Detect mismatches in both directions when reconciling a snapshot against enumerated durable jobs.
- Reject a durable row that embeds the snapshot mission under a different durable key.
- Also reject a durable row occupying the snapshot's key while embedding a different mission, even if direct lookup incorrectly returns no row.
- Add regression coverage for a corrupt key-to-mission mapping that would otherwise allow stale snapshot resurrection.

Acceptance: snapshot recovery only proceeds when the durable key and embedded mission identity agree in both directions across the enumerated index; either mismatch blocks recovery of the affected snapshot.


## M77 — Reject Duplicate Durable Identity Mappings
Status: COMPLETE

- Require the enumerated durable mission index to have a one-to-one mapping between durable job IDs and embedded mission IDs.
- Fail closed when duplicate durable keys or duplicate embedded mission IDs make recovery ambiguous.
- Add regression coverage proving duplicate identity rows cannot make a stale snapshot eligible for recovery.

Acceptance: snapshot recovery only proceeds when the enumerated durable identity index is readable, non-empty, consistent, and unambiguous.

## M78 — Preflight Durable Identity Index Before Snapshot Recovery
Status: COMPLETE

- Validate the full durable identity index before recovering any pending project snapshot, even when direct lookup returns a plausible matching job.
- Fail closed when enumeration fails, identities are unreadable/empty, mappings mismatch, or duplicate durable/embedded IDs exist.
- Add regressions for duplicate identity rows hidden by a successful direct lookup and for index enumeration failure.

Acceptance: no snapshot is restored based on a direct lookup until the configured enumerable durable identity index has passed a complete, consistent, one-to-one preflight.

## M79 — Require Explicit String Durable Identities
Status: COMPLETE

- Accept durable job IDs and embedded mission IDs only when they are explicit, non-empty strings.
- Reject null, numeric, blank, or otherwise non-string identity values during index preflight and snapshot reconciliation.
- Add regression coverage proving malformed identity types cannot make a pending snapshot recoverable.

Acceptance: durable recovery fails closed for non-string or empty identity fields rather than coercing arbitrary values into apparently valid identifiers.


## M80 — Enforce Strict Identities on Direct Job Lookup
Status: COMPLETE

- Apply the same explicit non-empty string identity validation to snapshot-backed direct job lookup results as to the preflight identity index.
- Do not coerce numeric or other malformed IDs into valid-looking strings during lifecycle reconciliation.
- Add a regression where the enumerated index is valid but direct lookup returns a corrupted job record.

Acceptance: every durable recovery path validates identity types consistently and refuses a malformed direct-lookup record.


## M81 — Validate Snapshot Mission Identity Before Recovery
Status: COMPLETE

- Validate the snapshot's mission ID as a canonical, non-empty string before checking duplicates or performing durable job lookup.
- Reject null, numeric, blank, or whitespace-padded IDs instead of allowing malformed legacy model instances to bypass normal validation.
- Add regression coverage for malformed snapshot mission IDs with no matching durable job.

Acceptance: no snapshot enters reconciliation, durable lookup, or queue restoration unless its mission identity is an explicit canonical non-empty string.

## Revised strategic improvement plan

See [docs/IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) for the research-backed priority sequence, exit gates, and milestone acceptance rules. The next planned work prioritizes end-to-end lifecycle reliability and evidence-based product QA over adding more autonomous agents.

### Planned milestones M82–M93

These are PLANNED, not complete. Promote one milestone to IN PROGRESS only when its implementation branch starts; mark COMPLETE only after tests and required GitHub checks pass.

- **M82 — Defensive Snapshot Record Decoding:** IN PROGRESS — validate record and nested-object shapes before dereferencing during restore.
- **M83 — Mixed-Record Restore Isolation:** corrupt records and persistence failures must not poison healthy recovery candidates.
- **M84 — Real-Path Mission Lifecycle Harness:** exercise submission through queue, worker, QA, and review with structured evidence.
- **M85 — Queue Liveness and Stuck-Stage Diagnostics:** deadlines, heartbeats, and actionable stuck/blocked state.
- **M86 — Idempotent Lifecycle Operations:** duplicate submissions and concurrent retry/cancel/revise/restart safety.
- **M87 — Generated Product QA Evidence:** build/startup smoke checks and browser critical-path checks for supported web products.
- **M88 — Independent Review and Approval Binding:** review findings and approval tied to exact source/artifact identity.
- **M89 — Tool Policy and Adversarial Safety Tests:** untrusted content, tool authorization, destructive action approval, and sandbox limits.
- **M90 — Customer Auth/Workspace End-to-End Acceptance:** OAuth, workspace membership, tenant isolation, and role separation.
- **M91 — Mission Observability and Budget Enforcement:** correlated event timeline, resource ceilings, and bounded autonomous scheduling.
- **M92 — Release Provenance and Rollback Readiness:** verifiable artifact provenance, SBOM where feasible, and rehearsed rollback.
- **M93 — Continuous Improvement Evaluation Loop:** measured quality, safety, latency, and cost regression gates.


## M82 — Defensive Snapshot Record Decoding
Status: IN PROGRESS

- Validate that each pending snapshot is a mapping before reading fields.
- Validate nested mission and plan objects are the expected model types before dereferencing their fields.
- Isolate parsing and sanitization exceptions to the affected record so malformed legacy data does not abort recovery of later healthy snapshots.
- Add mixed-record regressions covering null/scalar/list records, missing fields, wrong nested types, and malformed nested plans alongside a healthy snapshot.

Acceptance: malformed snapshot record shapes fail closed individually; a healthy independent snapshot later in the same restore batch is still restored, with no malformed record entering the queue.
