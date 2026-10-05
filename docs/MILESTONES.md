# AI Software Company — Master Milestone Roadmap

## Purpose

This file is the permanent source of truth for the AI Software Company roadmap.

The company must progress milestone by milestone.

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

Never skip milestones without an explicit decision.

---

# Completed Foundation

## M0 — Foundation & Planning
Status: COMPLETE

Project vision, architecture, lifecycle, engineering rules and roadmap established.

## M1 — Engineering Foundation
Status: COMPLETE

Core repository, Python environment, testing, linting and engineering foundation.

## M2 — AI Runtime
Status: COMPLETE

Initial AI runtime foundation.

## M3 — Agent Engine
Status: COMPLETE

Agent models, registry and execution engine.

## M4 — Task Engine
Status: COMPLETE

Task lifecycle and task state management.

## M5 — Master Manager
Status: COMPLETE

Company-level coordination foundation.

## M6 — Project Engine
Status: COMPLETE

Project lifecycle and project management foundation.

## M7 — Engineering Agents
Status: COMPLETE

Engineering-agent foundation.

## M8 — Sandbox
Status: COMPLETE

Sandbox execution foundation.

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

Core pipeline integration, runtime, tools, sandbox, persistence, GitHub, QA, memory, dashboard, security and end-to-end integration.

## M16 — Production Runtime & Prevention Infrastructure
Status: COMPLETE

Production runtime, lifecycle, monitoring, supervision, shutdown, metrics, alerting, backpressure, resource enforcement, timeout, recovery, persistence, GitHub runtime integration, QA runner, security, observability, dashboard, failure recovery, end-to-end execution and persistent memory/context prevention.

---

# Current Roadmap

## M17 — Memory Integration
Status: NEXT

Connect persistent memory to the actual company.

Scope:
- Agent memory
- Task memory
- Project memory
- Mission memory
- Decision memory
- Failure memory
- Recovery memory
- QA memory
- Execution memory
- Context retrieval before agent execution
- Memory writing after execution
- Handoff context
- Restart context
- Cross-agent context

Goal:
The company should not lose important context between tasks, agents or executions.

---

## M18 — Real AI Model Layer
Status: NOT STARTED

Build the production model abstraction.

Scope:
- Model provider abstraction
- Local models
- Cloud models
- Model routing
- Fallback models
- Token tracking
- Context limits
- Model capability registry
- Model selection
- Structured output
- Streaming
- Retry handling
- Model health
- Provider failure recovery

Goal:
Agents can use real AI models through a stable internal interface.

---

## M19 — AI CEO / Master Manager
Status: NOT STARTED

Build the autonomous company decision-maker.

Scope:
- Mission interpretation
- Goal decomposition
- Project selection
- Priority management
- Agent assignment
- Resource allocation
- Task delegation
- Progress monitoring
- Decision memory
- Failure handling
- Human escalation
- Company-level planning

Goal:
A human gives a mission and the AI CEO converts it into executable company work.

---

## M20 — Universal Tool System
Status: NOT STARTED

Build the standard tool layer used by all agents.

Scope:
- Filesystem
- Terminal
- Git
- GitHub
- Web research
- HTTP/API
- Database
- Python execution
- Testing
- Package management
- Tool permissions
- Tool security
- Tool logging
- Tool timeout
- Tool resource limits

Goal:
Agents can safely interact with the real development environment.

---

## M21 — Real Project Factory
Status: NOT STARTED

Build the system that turns an approved idea into a real software project.

Scope:
- Project discovery
- Requirements
- Product definition
- Architecture
- Technology selection
- Repository creation
- Project initialization
- Task generation
- Agent assignment
- Project lifecycle
- Project memory

Goal:
The company can autonomously start a real software project.

---

## M22 — Autonomous Engineering
Status: NOT STARTED

Build the engineering execution system.

Scope:
- Code generation
- Code modification
- File creation
- Dependency installation
- Git branches
- Commits
- Pull requests
- Code review
- Refactoring
- Documentation
- Build execution

Goal:
Agents can independently implement software tasks.

---

## M23 — Autonomous QA & Debugging 2.0
Status: PARTIALLY COMPLETE

Upgrade QA from a runner into an autonomous quality system.

Scope:
- Test generation
- Test execution
- Failure analysis
- Root-cause detection
- Automatic fixes
- Regression testing
- Quality scoring
- Retry loops
- Bug memory
- QA reports
- Release gates

Goal:
The company can find and fix its own software failures.

---

## M24 — Production Security & Governance
Status: PARTIALLY COMPLETE

Harden the company against unsafe autonomous actions.

Scope:
- Permission system
- Agent capabilities
- Tool allowlists
- Secret protection
- Data isolation
- Sandbox policies
- Repository protection
- Human approval gates
- Dangerous-operation controls
- Audit trails
- Policy enforcement

Goal:
Autonomous does not mean unrestricted.

---

## M25 — Self-Healing & Recovery
Status: PARTIALLY COMPLETE

Build company-wide recovery.

Scope:
- Runtime failure recovery
- Agent failure recovery
- Task retry
- Project recovery
- State restoration
- Crash recovery
- Restart recovery
- Checkpointing
- Failure diagnosis
- Recovery strategies
- Escalation

Goal:
The company can recover from failures without losing its work.

---

## M26 — Production Memory & Knowledge Engine
Status: NOT STARTED

Upgrade the initial memory system into production-grade knowledge infrastructure.

Scope:
- PostgreSQL persistence
- Semantic embeddings
- Vector search
- Hybrid retrieval
- Memory ranking
- Long-term knowledge
- Short-term context
- Episodic memory
- Semantic memory
- Procedural memory
- Memory consolidation
- Duplicate detection
- Memory expiration
- Knowledge graphs

Goal:
The company develops persistent organizational knowledge.

---

## M27 — Agent Registry & Agent Marketplace
Status: NOT STARTED

Build the complete agent ecosystem.

Scope:
- Agent registry
- Agent capabilities
- Agent versions
- Agent performance
- Agent specialization
- Agent health
- Agent selection
- Agent lifecycle
- Agent templates
- Agent composition

Goal:
The company can dynamically select the best agent for each task.

---

## M28 — Artifact & Document System
Status: NOT STARTED

Build centralized company artifacts.

Scope:
- Specifications
- Architecture documents
- Design documents
- Research
- Test reports
- QA reports
- Decisions
- Project documentation
- Release notes
- Agent reports
- Artifact versioning

Goal:
Important company knowledge exists as durable artifacts.

---

## M29 — Project State & Control Plane
Status: NOT STARTED

Create the authoritative state system.

Scope:
- Company state
- Project state
- Task state
- Agent state
- Runtime state
- Dependency state
- Release state
- Recovery state
- State transitions
- Checkpoints
- Event history

Goal:
The company always knows what is happening and what must happen next.

---

## M30 — Human Control Center
Status: NOT STARTED

Create the human oversight interface.

Scope:
- Mission submission
- Project approval
- Agent monitoring
- Task monitoring
- Logs
- Memory
- Costs
- Security alerts
- Approval requests
- Pause/resume
- Stop
- Override
- Manual intervention

Goal:
Humans remain in control while the company operates autonomously.

---

## M31 — Deployment & Infrastructure Engine
Status: NOT STARTED

Build autonomous deployment.

Scope:
- Build
- Package
- Containers
- Deployment
- Environment management
- Infrastructure provisioning
- Health checks
- Rollbacks
- Deployment validation
- Release management

Goal:
The company can take software from source code to production.

---

## M32 — Real-World Research Engine
Status: NOT STARTED

Build autonomous research.

Scope:
- Web research
- Documentation research
- Market research
- Technology research
- Competitor analysis
- Source validation
- Fact checking
- Research memory
- Research reports

Goal:
The company can understand the world before building.

---

## M33 — Multi-Agent Collaboration
Status: NOT STARTED

Enable agents to work together.

Scope:
- Agent communication
- Shared context
- Task handoffs
- Parallel work
- Dependency coordination
- Peer review
- Debate
- Conflict resolution
- Agent synchronization

Goal:
Multiple specialized agents operate as one engineering organization.

---

## M34 — Company Dashboard
Status: PARTIALLY COMPLETE

Create the complete company control dashboard.

Scope:
- Company overview
- Active projects
- Agents
- Tasks
- Runtime
- Memory
- QA
- Security
- Costs
- Deployments
- Failures
- Research
- Metrics
- Audit

Goal:
One place to understand the entire autonomous company.

---

## M35 — Continuous Learning Engine
Status: NOT STARTED

Turn experience into improvement.

Scope:
- Failure analysis
- Success analysis
- Agent performance
- Strategy evaluation
- Process optimization
- Prompt improvement
- Tool improvement
- Workflow improvement
- Knowledge consolidation
- Benchmark-driven learning

Goal:
The company becomes better through experience.

---

## M36 — End-to-End Autonomous Project
Status: NOT STARTED

Run the complete company on a real software project.

Flow:

MISSION
→ AI CEO
→ RESEARCH
→ PRODUCT DEFINITION
→ ARCHITECTURE
→ TASK BREAKDOWN
→ AGENT ASSIGNMENT
→ ENGINEERING
→ QA
→ DEBUGGING
→ SECURITY
→ CODE REVIEW
→ GITHUB
→ DEPLOYMENT
→ MONITORING
→ FEEDBACK
→ MEMORY
→ IMPROVEMENT

Goal:
Build the first genuinely real project autonomously.

---

## M37 — Autonomous Software Company Acceptance
Status: NOT STARTED

Formal acceptance test for the company.

Requirements:
- Real mission
- Real project
- Real repository
- Real agents
- Real AI models
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

Goal:
Prove that the system behaves as an autonomous software company.

---

# Advanced Production Milestones

## M38 — Billing, Cost & Budget Control
Status: NOT STARTED

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
The company can operate economically and prevent uncontrolled spending.

---

## M39 — Compliance, Privacy & Data Governance
Status: NOT STARTED

Scope:
- Data classification
- PII detection
- Sensitive-data handling
- Retention policies
- Data deletion
- Data export
- Audit
- Repository isolation
- Open-source license compliance
- Dependency license checks

Goal:
The company operates safely with real-world data and software.

---

## M40 — Evaluation & Benchmarking
Status: NOT STARTED

Scope:
- Agent benchmarks
- Coding benchmarks
- QA benchmarks
- Research benchmarks
- Regression benchmarks
- Model comparison
- Agent comparison
- Autonomous-run scoring
- Quality history

Goal:
Measure whether the company is actually improving.

---

## M41 — Scalability & Distributed Execution
Status: NOT STARTED

Scope:
- Multiple workers
- Distributed queues
- Concurrent projects
- Scheduling
- Resource allocation
- Horizontal scaling
- Fault-tolerant coordination
- Worker health

Goal:
Move from a single-machine company to a scalable software factory.

---

## M42 — Company Operations & Economics
Status: NOT STARTED

Scope:
- Project prioritization
- Opportunity scoring
- Development cost
- Revenue estimation
- ROI
- Portfolio management
- Project abandonment
- Resource allocation
- Business strategy

Goal:
The AI company can make rational portfolio-level decisions.

---

## M43 — Autonomous Product Lifecycle
Status: NOT STARTED

Lifecycle:

BUILD
→ DEPLOY
→ MONITOR
→ OBSERVE
→ RECEIVE FEEDBACK
→ DETECT BUGS/FEATURES
→ PRIORITIZE
→ IMPLEMENT
→ TEST
→ DEPLOY

Goal:
Products continuously evolve after their initial release.

---

## M44 — Production Reliability / SRE
Status: NOT STARTED

Scope:
- Monitoring
- Alerting
- Incident management
- Logs
- Metrics
- Distributed tracing
- Health checks
- Backups
- Disaster recovery
- Rollbacks
- SLA/SLO
- Reliability engineering

Goal:
Operate autonomous software reliably in production.

---

## M45 — Final Security & Red-Team Validation
Status: NOT STARTED

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
- Adversarial testing

Goal:
Attempt to break the autonomous company before trusting it with real-world operation.

---

## M46+ — Continuous Autonomous Evolution
Status: FUTURE

The company becomes continuously self-improving.

Scope:
- Continuous project generation
- Continuous learning
- Agent evolution
- Workflow evolution
- Tool evolution
- Infrastructure evolution
- Self-evaluation
- Self-optimization
- New project discovery
- Portfolio evolution

Goal:

MISSION
→ BUILD
→ DEPLOY
→ LEARN
→ IMPROVE
→ BUILD NEXT
→ REPEAT

The company continuously evolves while remaining within human-defined safety and governance boundaries.

---

# Milestone Execution Rule

Always work on exactly one active milestone.

Current milestone:

**M17 — Memory Integration**

After completing a milestone, update this file:

`Status: COMPLETE`

Then commit and push the change before starting the next milestone.

Never rely on chat history alone for the roadmap.

GitHub repository + this file are the persistent roadmap source of truth.
M21 Agent Tool Integration — COMPLETE
M22 AI Tool-Calling Integration — NEXT
