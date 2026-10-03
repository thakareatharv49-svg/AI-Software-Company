# AI Software Company — Milestones

## Purpose

Milestones are objective checkpoints for the development of the AI Software Company.

A milestone is complete only when its acceptance criteria pass.

---

# M0 — Company Blueprint

## Goal

Establish the permanent design and operating model of the company.

## Deliverables

* Master Plan
* Development Roadmap
* Project Lifecycle
* Company Model
* Agent System
* Architecture
* Security Model
* GitHub Model
* Quality Gate Model
* Memory Model

## Acceptance Criteria

* [x] Repository initialized
* [x] Main branch created
* [x] Master Plan committed
* [ ] Roadmap committed
* [ ] Milestones committed
* [ ] Initial documentation reviewed

## Current Status

**IN PROGRESS**

---

# M1 — Engineering Foundation

## Goal

Create the executable software foundation.

## Deliverables

* Python project
* Package structure
* Configuration system
* Environment management
* Logging
* Error handling
* Testing framework
* Type checking
* Linting
* Docker foundation
* CI

## Acceptance Criteria

* [ ] Application starts successfully
* [ ] Configuration loads
* [ ] Logging works
* [ ] Unit tests run
* [ ] CI runs
* [ ] Docker image builds
* [ ] Basic health check works

---

# M2 — AI Runtime

## Goal

Make the company capable of communicating with an AI model.

## Deliverables

* Model interface
* Ollama integration
* Model registry
* Model configuration
* Prompt manager
* Response parser
* Retry handling
* Model usage logging

## Acceptance Criteria

* [ ] Local model can be discovered
* [ ] Model can receive a structured request
* [ ] Response can be parsed
* [ ] Invalid response is handled
* [ ] Model failure is handled
* [ ] Automated tests pass

---

# M3 — First Agent

## Goal

Create the first real AI agent.

## Deliverables

* Agent definition
* Agent registry
* Agent runtime
* Agent context
* Agent permissions
* Agent result format

## Acceptance Criteria

* [ ] Agent can be registered
* [ ] Agent can be loaded
* [ ] Agent can receive a task
* [ ] Agent can call an allowed tool
* [ ] Agent returns structured output
* [ ] Agent state is recorded
* [ ] Permission restrictions work

---

# M4 — Tool System

## Goal

Allow agents to interact with software safely.

## Initial Tools

* File reader
* File writer
* File editor
* Code search
* Terminal
* Git
* Testing

## Acceptance Criteria

* [ ] Tool registry works
* [ ] Tools have schemas
* [ ] Agent permissions are enforced
* [ ] Tool calls are logged
* [ ] Tool failures are handled
* [ ] Dangerous operations are restricted

---

# M5 — Task Engine

## Goal

Create the company's internal work-management system.

## Deliverables

* Task model
* Task states
* Dependencies
* Scheduler
* Assignment system
* Retry system
* Task persistence
* Task events

## Acceptance Criteria

* [ ] Task can be created
* [ ] Task can be assigned
* [ ] Dependencies work
* [ ] Ready tasks are scheduled
* [ ] Running tasks are tracked
* [ ] Failed tasks retry
* [ ] Blocked tasks are recorded
* [ ] Completed tasks are persisted

---

# M6 — Master Manager

## Goal

Create the central company coordinator.

## Responsibilities

* Mission interpretation
* Project planning
* Task creation
* Agent assignment
* Progress monitoring
* Failure handling
* Decision making
* State transitions

## Acceptance Criteria

The Manager must successfully coordinate:

```text
Mission
  ↓
Project
  ↓
Tasks
  ↓
Agent
  ↓
Execution
  ↓
Result
```

without manually creating every task.

---

# M7 — Project Engine

## Goal

Create complete project lifecycle management.

## Acceptance Criteria

A project can move through:

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

with persistent state.

---

# M8 — First Software Project

## Goal

The company builds its first meaningful software project.

This is the first major proof that the system is more than an agent framework.

## Required Flow

```text
Manager
   ↓
Project
   ↓
Architecture
   ↓
Tasks
   ↓
Engineering Agent
   ↓
Code
   ↓
Tests
   ↓
Review
   ↓
Release
```

## Acceptance Criteria

* [ ] Real software is produced
* [ ] Source code is usable
* [ ] Tests pass
* [ ] Documentation exists
* [ ] Git history is meaningful
* [ ] Project can be reproduced

---

# M9 — Sandbox

## Goal

Run autonomous engineering safely.

## Acceptance Criteria

* [ ] Project runs inside Docker
* [ ] Agent cannot access arbitrary host files
* [ ] CPU limits work
* [ ] Memory limits work
* [ ] Runtime limits work
* [ ] Workspace isolation works
* [ ] Cleanup works

---

# M10 — Autonomous QA

## Goal

Allow the company to validate its own software.

## Acceptance Criteria

* [ ] Unit tests execute
* [ ] Integration tests execute
* [ ] E2E tests execute where applicable
* [ ] Build validation works
* [ ] Failures are detected
* [ ] Failure context is captured
* [ ] Regression tests work

---

# M11 — Autonomous Debugging

## Goal

Allow agents to repair software failures.

## Required Loop

```text
Failure
  ↓
Analysis
  ↓
Hypothesis
  ↓
Fix
  ↓
Test
  ↓
Pass / Retry / Block
```

## Acceptance Criteria

* [ ] Agent receives failure information
* [ ] Agent analyzes failure
* [ ] Agent proposes a fix
* [ ] Fix is applied safely
* [ ] Tests rerun
* [ ] Retry limit is enforced
* [ ] Unresolved issues become BLOCKED

---

# M12 — Security Gate

## Goal

Prevent insecure software from being released.

## Acceptance Criteria

* [ ] Secret scanning
* [ ] Dependency scanning
* [ ] Basic vulnerability checks
* [ ] Authentication review
* [ ] Authorization review
* [ ] Input validation review
* [ ] Unsafe command detection
* [ ] Security report generated

Critical security failures block release.

---

# M13 — Independent Code Review

## Goal

Introduce independent review before release.

## Acceptance Criteria

* [ ] Reviewer receives implementation
* [ ] Reviewer receives requirements
* [ ] Reviewer evaluates architecture
* [ ] Reviewer evaluates security
* [ ] Reviewer evaluates tests
* [ ] Reviewer produces structured review
* [ ] Failed review creates follow-up tasks
* [ ] Approved review allows quality gate progression

---

# M14 — GitHub Automation

## Goal

Allow the company to operate through GitHub.

## Acceptance Criteria

* [ ] Repository creation
* [ ] Branch creation
* [ ] Commit creation
* [ ] Push
* [ ] Issue creation
* [ ] Pull request creation
* [ ] Review requests
* [ ] Merge workflow
* [ ] Release creation

All actions must use controlled permissions.

---

# M15 — Quality Gate

## Goal

Create the final release decision mechanism.

## Required Checks

```text
Requirements
Architecture
Implementation
Tests
Security
Code Review
Documentation
Build
Deployment
GitHub
```

## Acceptance Criteria

No project reaches `RELEASE` unless all required gates pass.

---

# M16 — Project Memory

## Goal

Give every project persistent knowledge.

## Stored Information

* Requirements
* Architecture
* Decisions
* Tasks
* Failures
* Fixes
* Tests
* Releases
* Deployment
* Lessons

## Acceptance Criteria

A completed project can be reconstructed from its stored information.

---

# M17 — Company Memory

## Goal

Allow the company to learn across projects.

## Stored Information

* Successful approaches
* Failed approaches
* Agent performance
* Technology lessons
* Architecture lessons
* Security lessons
* Testing lessons
* Resource usage
* Project outcomes

## Acceptance Criteria

A future project can retrieve relevant lessons from previous projects.

---

# M18 — Self-Improvement

## Goal

Allow controlled improvement of company processes.

## Required Process

```text
Proposal
 ↓
Evaluation
 ↓
Experiment
 ↓
Testing
 ↓
Review
 ↓
Approval
 ↓
Deployment
 ↓
Monitoring
```

## Acceptance Criteria

* [ ] Improvement proposals are recorded
* [ ] Experiments run in isolation
* [ ] Results are measured
* [ ] Review is performed
* [ ] Unsafe changes are rejected
* [ ] Improvements are versioned

---

# M19 — Company Dashboard

## Goal

Give the human complete operational visibility.

## Acceptance Criteria

Dashboard displays:

* [ ] Projects
* [ ] Agents
* [ ] Tasks
* [ ] Activity
* [ ] Logs
* [ ] Tests
* [ ] Security
* [ ] GitHub
* [ ] Memory
* [ ] Releases
* [ ] Resource usage

---

# M20 — First End-to-End Autonomous Run

## Goal

Demonstrate the complete company loop.

## Required Flow

```text
Human Mission
      ↓
Research
      ↓
Project Selection
      ↓
Product Definition
      ↓
Architecture
      ↓
Task Breakdown
      ↓
Engineering
      ↓
Testing
      ↓
Debugging
      ↓
Security
      ↓
Code Review
      ↓
GitHub
      ↓
Release
      ↓
Memory
```

## Acceptance Criteria

The entire flow executes with minimal human intervention while respecting all permission and quality gates.

---

# M21 — Continuous Company

## Goal

Reach the long-term operating model.

After a project reaches `COMPLETED`:

```text
Completed Project
       ↓
Analyze Results
       ↓
Store Lessons
       ↓
Research Next Opportunity
       ↓
Select Next Project
       ↓
Build
       ↓
Release
       ↺
```

## Acceptance Criteria

The company can continuously move from one approved project to the next without requiring manual reconstruction of its internal state.

---

# Milestone Philosophy

A milestone is not complete because:

* Files exist.
* Agents respond.
* Code compiles once.
* A demo was manually fixed.
* A GitHub commit was created.

A milestone is complete when its defined behavior works repeatedly and is covered by tests.

---

# Major Proof Points

The most important demonstrations are:

## Proof 1

```text
One model
 ↓
One agent
 ↓
One tool
```

## Proof 2

```text
One manager
 ↓
One task
 ↓
One agent
 ↓
One result
```

## Proof 3

```text
Manager
 ↓
Project
 ↓
Tasks
 ↓
Engineering
 ↓
Tests
```

## Proof 4

```text
Failure
 ↓
Debug
 ↓
Fix
 ↓
Retest
```

## Proof 5

```text
Complete Project
 ↓
GitHub
 ↓
Release
 ↓
Memory
```

## Final Proof

```text
Mission
 ↓
Autonomous Company
 ↓
Useful Software
 ↓
Release
 ↓
Learning
 ↓
Next Project
```

---

# Current Milestone

**M0 — Company Blueprint**

Next implementation target:

**M1 — Engineering Foundation**
