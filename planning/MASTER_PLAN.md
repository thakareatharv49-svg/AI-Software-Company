# AI Software Company — Master Plan

## 1. Vision

Build a continuously operating, open-source-first AI software company that can research problems, select software opportunities, design products, build them, test them, secure them, release them, learn from the results, and begin the next project.

The human provides the company's mission and strategic direction.

AI agents perform the operational work under controlled permissions, quality gates, and resource limits.

The company should become increasingly autonomous without sacrificing reliability, security, transparency, or human control.

---

## 2. Core Principle

The company is not a collection of chatbots.

It is an operating system for autonomous software development.

```text
Human Mission
      ↓
Master Manager
      ↓
Research
      ↓
Opportunity Selection
      ↓
Product Definition
      ↓
Architecture
      ↓
Task Breakdown
      ↓
Engineering
      ↓
Sandbox
      ↓
Testing
      ↓
Debugging
      ↓
Security
      ↓
Code Review
      ↓
Quality Gate
      ↓
GitHub / Release
      ↓
Monitoring
      ↓
Memory
      ↓
Next Project
      ↺
```

---

## 3. Company Objectives

The system must eventually be able to:

1. Understand a high-level mission.
2. Research software opportunities.
3. Propose and evaluate projects.
4. Define product requirements.
5. Design system architecture.
6. Break work into structured tasks.
7. Assign tasks to specialized agents.
8. Execute engineering work inside isolated environments.
9. Run tests automatically.
10. Diagnose and repair failures.
11. Perform security checks.
12. Perform independent code review.
13. Maintain documentation.
14. Manage Git repositories and GitHub workflows.
15. Release completed software.
16. Monitor projects.
17. Store project and company knowledge.
18. Learn from previous projects.
19. Improve its processes through controlled experiments.
20. Continue to the next project after completion.

---

## 4. Human Role

The human is the owner and strategic authority.

The human should primarily provide:

* Mission
* Strategic objectives
* Important constraints
* Resource boundaries
* Approval for sensitive operations

The system should handle routine operational decisions autonomously.

The company must never assume that autonomy means unrestricted access.

---

## 5. Master Manager

The Master Manager is the central coordinator.

Responsibilities:

* Understand company mission.
* Maintain company state.
* Select projects.
* Create project plans.
* Allocate resources.
* Assign agents.
* Monitor progress.
* Resolve task dependencies.
* Detect blocked projects.
* Trigger testing and review.
* Enforce quality gates.
* Coordinate releases.
* Record important decisions.
* Start the next project.

The Master Manager should coordinate specialized agents rather than perform every specialized task itself.

---

## 6. Departments

### Strategy / Management

Responsible for company-level planning and coordination.

### Research

Finds software opportunities, user problems, technical possibilities, and relevant evidence.

### Product

Converts opportunities into product requirements.

### Architecture

Designs technical systems, APIs, databases, infrastructure, security boundaries, and testing strategies.

### Engineering

Includes:

* Frontend
* Backend
* AI
* Database
* Infrastructure

### QA

Responsible for:

* Unit tests
* Integration tests
* End-to-end tests
* Regression tests
* Build validation

### Debugging

Investigates failures and creates controlled fixes.

### Security

Checks:

* Secrets
* Authentication
* Authorization
* Input validation
* Injection vulnerabilities
* XSS
* CSRF
* Dependency vulnerabilities
* Unsafe commands
* Container security
* API exposure

### Code Review

Independently reviews implementation quality.

### DevOps

Responsible for:

* Builds
* CI
* Deployment
* Releases
* Environment configuration
* Monitoring
* Rollbacks

### Documentation

Maintains technical and user documentation.

### Memory

Maintains project, company, technical, decision, and failure knowledge.

---

## 7. Agent Model

Every agent has:

* Identity
* Role
* Capabilities
* Instructions
* Tools
* Permissions
* Resource limits
* Model configuration
* Retry limits
* Timeout
* Output format

Example:

```yaml
agent:
  name: backend_engineer
  role: backend development

  capabilities:
    - python
    - fastapi
    - postgresql

  tools:
    - read_file
    - write_file
    - edit_file
    - terminal
    - git
    - testing

  limits:
    max_runtime: 30m
    max_retries: 5
```

Agents must not receive unrestricted system access.

---

## 8. Task System

All work is represented as structured tasks.

```text
PROJECT
   ↓
EPIC
   ↓
TASK
   ↓
SUBTASK
```

Each task contains:

* ID
* Project
* Description
* Requirements
* Dependencies
* Assigned agent
* Status
* Priority
* Inputs
* Outputs
* Attempts
* Errors
* Tests
* Git changes
* Completion criteria

Possible states:

```text
PENDING
READY
RUNNING
BLOCKED
FAILED
RETRYING
REVIEW
COMPLETED
CANCELLED
```

---

## 9. Project Lifecycle

Every project follows a controlled state machine:

```text
IDEA
 ↓
RESEARCH
 ↓
VALIDATION
 ↓
PLANNING
 ↓
ARCHITECTURE
 ↓
DEVELOPMENT
 ↓
TESTING
 ↓
DEBUGGING
 ↓
SECURITY
 ↓
REVIEW
 ↓
RELEASE
 ↓
MONITORING
 ↓
COMPLETED
```

Failure states:

```text
BLOCKED
CANCELLED
ABANDONED
```

A project cannot be marked `COMPLETED` merely because files were generated.

---

## 10. Engineering Environment

Projects must run inside isolated environments whenever possible.

Primary technology:

* Docker
* Git
* GitHub
* Python
* FastAPI
* PostgreSQL
* React/Next.js where appropriate

The system should prefer reproducible environments.

Agents should not freely modify the host operating system.

---

## 11. Tool System

Agents interact with the environment through controlled tools.

Initial tools:

```text
filesystem
terminal
git
github
docker
testing
research
```

Example filesystem tools:

```text
read_file
write_file
edit_file
search_code
```

Example Git tools:

```text
git_status
git_diff
git_branch
git_commit
git_push
```

Example GitHub tools:

```text
create_repository
create_branch
create_pull_request
request_review
merge_pull_request
create_release
```

Dangerous operations require explicit permission boundaries.

---

## 12. GitHub as Company Headquarters

GitHub is the company's engineering source of truth.

The main company repository stores:

* Vision
* Architecture
* Master plan
* Roadmap
* Decisions
* Agent specifications
* Company policies
* Source code
* Tests
* Infrastructure
* Memory schemas
* Documentation
* Project records

GitHub Issues represent work.

Pull Requests represent proposed changes.

GitHub Actions provide automated CI.

Git history provides engineering history.

Releases represent stable versions.

Secrets must never be committed to Git.

---

## 13. Git Strategy

The company should create meaningful commits.

Examples:

```text
feat: add task scheduler
fix: resolve task retry state bug
test: add scheduler integration tests
refactor: simplify agent registry
docs: document project lifecycle
security: restrict terminal permissions
```

The objective is meaningful engineering history, not artificial commit volume.

---

## 14. Model Strategy

The company should be open-source-first.

Primary approach:

```text
Local Model Runtime
       ↓
Model Router
       ↓
Task Complexity
       ↓
Appropriate Model
```

Possible runtime:

* Ollama
* Other compatible local runtimes later

The system should support different model sizes for different tasks.

Simple tasks should use smaller models.

Complex architecture, debugging, and reasoning tasks can use stronger models when hardware allows.

No mandatory commercial AI API should be required for the core system.

---

## 15. Resource Manager

Local hardware is limited.

The Resource Manager controls:

* CPU
* RAM
* Concurrent agents
* Model selection
* Task priority
* Runtime limits

Initially, the company should prefer sequential or low-concurrency execution.

Later it can support:

```text
Machine 1
Machine 2
Machine 3
Cloud/remote workers
```

forming a distributed compute pool.

---

## 16. Event System

Agents should communicate through structured events.

Examples:

```text
PROJECT_CREATED
TASK_CREATED
TASK_STARTED
TASK_COMPLETED
TEST_FAILED
BUG_FOUND
FIX_APPLIED
REVIEW_REQUESTED
REVIEW_FAILED
PR_CREATED
PR_MERGED
RELEASE_CREATED
PROJECT_COMPLETED
```

The event system allows the company to become event-driven rather than dependent on constant polling.

---

## 17. Quality Gate

A project can only become completed when required gates pass.

Minimum gates:

```text
Requirements       ✓
Architecture       ✓
Implementation     ✓
Unit Tests         ✓
Integration Tests  ✓
E2E Tests          ✓
Security           ✓
Code Review        ✓
Documentation      ✓
Build              ✓
Deployment         ✓
GitHub State       ✓
```

Any critical failure blocks release.

---

## 18. Autonomous Debugging

When a test fails:

```text
TEST FAILURE
     ↓
ERROR ANALYSIS
     ↓
HYPOTHESIS
     ↓
FIX
     ↓
RETEST
     ↓
PASS? ── YES → CONTINUE
  │
  NO
  ↓
RETRY
```

Retries are limited.

Example:

```text
Maximum retries = 5
```

If unresolved:

```text
PROJECT → BLOCKED
```

The system records:

* Failure
* Hypothesis
* Attempt
* Fix
* Result
* Final reason

---

## 19. Security Model

Default principle:

> Agents receive the minimum permissions required for their task.

Example:

```text
Read project files       ✓
Write project files      ✓
Run project tests        ✓
Git commit               ✓
Git push                 ✓
Create PR                ✓

Read passwords           ✗
Access personal files    ✗
Delete arbitrary repos   ✗
Execute unrestricted host commands ✗
```

Sensitive actions should have separate permission gates.

---

## 20. Memory System

Memory has multiple layers.

### Project Memory

Stores:

* Requirements
* Architecture
* Decisions
* Technologies
* Bugs
* Fixes
* Tests
* Deployment information

### Company Memory

Stores:

* Project outcomes
* Agent performance
* Successful strategies
* Failed strategies
* Technology lessons
* Resource usage

### Technical Memory

Stores reusable:

* Bug fixes
* Architecture patterns
* Security lessons
* Testing strategies
* Engineering patterns

### Decision Memory

Stores important decisions and their rationale.

---

## 21. Self-Improvement

The company may improve its own processes, but not without safeguards.

Process:

```text
Improvement Proposal
       ↓
Evaluation
       ↓
Sandbox Experiment
       ↓
Tests
       ↓
Independent Review
       ↓
Approval Gate
       ↓
Deploy
       ↓
Monitor
```

The system must not freely rewrite its own core orchestration without controlled evaluation.

---

## 22. Documentation Standard

Every serious project should produce:

```text
README.md
ARCHITECTURE.md
CONTRIBUTING.md
API documentation
Setup documentation
Environment documentation
Deployment guide
Testing guide
CHANGELOG.md
```

The company itself must maintain equivalent documentation.

---

## 23. Observability

The company must record:

* Agent actions
* Tool calls
* Task execution
* Project state changes
* Test results
* Errors
* Resource usage
* Git operations
* Releases
* Security events

The goal is complete operational visibility.

---

## 24. Dashboard

The eventual dashboard contains:

```text
Dashboard
Projects
Agents
Tasks
GitHub
Memory
Activity
Logs
Tests
Security
Releases
Settings
```

Project view:

```text
Overview
Requirements
Architecture
Tasks
Agents
Code
Tests
Security
GitHub
Logs
Decisions
Memory
```

Agent view:

```text
Status
Current Task
Model
Tools
Permissions
Last Action
Performance
```

---

## 25. Autonomy Levels

### Level 0 — Manual

Human controls every action.

### Level 1 — Assisted

AI recommends actions.

### Level 2 — Supervised Autonomy

AI executes routine work with human oversight.

### Level 3 — Autonomous Projects

AI can independently complete approved projects.

### Level 4 — Continuous Company

AI continuously researches, builds, releases, learns, and begins new projects.

The target architecture is Level 4.

---

## 26. Initial Architecture

```text
                HUMAN
                  │
                  ▼
          MASTER MANAGER
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
     PROJECT             COMPANY
     ENGINE               STATE
        │
        ▼
    TASK ENGINE
        │
        ▼
   AGENT REGISTRY
        │
        ▼
      AGENTS
        │
        ▼
      TOOLS
        │
   ┌────┴─────┐
   ▼          ▼
SANDBOX     GITHUB
   │
   ▼
TESTING
   │
   ▼
QUALITY GATE
   │
   ▼
RELEASE
   │
   ▼
MEMORY
```

---

## 27. Development Order

We will build the system in this order:

### Phase 0

Foundation

### Phase 1

AI Runtime

### Phase 2

Agent Engine

### Phase 3

Task Engine

### Phase 4

Master Manager

### Phase 5

Project Engine

### Phase 6

Engineering Agents

### Phase 7

Sandbox

### Phase 8

Testing and Debugging

### Phase 9

Security and Code Review

### Phase 10

GitHub Automation

### Phase 11

Memory

### Phase 12

Dashboard

### Phase 13

Continuous Autonomous Operation

---

## 28. First Engineering Principle

We do not begin by creating many autonomous agents.

We first make this reliable:

```text
MODEL
  ↓
AGENT
  ↓
TOOLS
  ↓
TASK
  ↓
PROJECT
  ↓
MANAGER
  ↓
QUALITY GATE
```

Once this foundation is stable, specialized departments can be added safely.

---

## 29. Definition of Success

The company is successful when a human can provide a high-level software mission and the system can reliably:

```text
Understand
   ↓
Research
   ↓
Plan
   ↓
Design
   ↓
Build
   ↓
Test
   ↓
Debug
   ↓
Secure
   ↓
Review
   ↓
Release
   ↓
Learn
   ↓
Build Again
```

with meaningful engineering artifacts, reproducible execution, controlled permissions, transparent state, and persistent knowledge.
