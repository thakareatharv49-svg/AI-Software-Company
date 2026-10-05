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
Status: IMPLEMENTED / FINAL VALIDATION PENDING

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
Status: IMPLEMENTED / FINAL VALIDATION PENDING

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
Status: IMPLEMENTED / FINAL VALIDATION PENDING

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
Status: IMPLEMENTED / FINAL VALIDATION PENDING

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

## M41 — Scalability & Distributed Execution
Status: NEXT

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
Status: NOT STARTED

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
Status: NOT STARTED

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
Status: NOT STARTED

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
Status: NOT STARTED

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
Status: NOT STARTED

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
