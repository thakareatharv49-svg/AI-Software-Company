# AI Software Company — Development Roadmap

## Purpose

This roadmap defines the implementation order for the AI Software Company.

The system will be built incrementally.

Each phase must have a working, testable result before the next major phase begins.

---

# Phase 0 — Foundation

## Objective

Establish the repository, documentation, development environment, configuration system, logging, testing foundation, and core project structure.

## Deliverables

* Git repository
* Documentation structure
* Python project
* Configuration system
* Environment variable support
* Logging
* Error handling foundation
* Test framework
* Basic CI
* Docker foundation
* Architecture decision process

## Completion Criteria

* Python environment works
* Tests execute successfully
* Configuration loads correctly
* Logging works
* CI runs successfully
* Repository structure is documented

## Status

Completed documentation foundation.

---

# Phase 1 — AI Runtime

## Objective

Create the foundation for communicating with local AI models.

## Components

```text
AI Runtime
├── Model Interface
├── Ollama Adapter
├── Model Registry
├── Model Router
├── Prompt Manager
├── Context Manager
└── Response Parser
```

## Capabilities

The runtime must be able to:

1. Select a model.
2. Send structured prompts.
3. Receive responses.
4. Validate responses.
5. Handle failures.
6. Retry safely.
7. Record model usage.
8. Support future model providers.

## Completion Criteria

* Local model can be called.
* Model responses are normalized.
* Invalid responses are handled.
* Model configuration is externalized.
* Runtime has automated tests.

---

# Phase 2 — Agent Engine

## Objective

Create the standard execution model for AI agents.

## Components

```text
Agent Engine
├── Agent Definition
├── Agent Registry
├── Agent Runtime
├── Agent Context
├── Agent Permissions
├── Agent Tools
├── Agent State
└── Agent Result
```

## Agent lifecycle

```text
CREATED
 ↓
READY
 ↓
RUNNING
 ↓
COMPLETED
```

Failure path:

```text
RUNNING
 ↓
FAILED
 ↓
RETRY
 ↓
BLOCKED
```

## Completion Criteria

* Agents can be registered.
* Agents can be loaded.
* Agents can receive tasks.
* Agents can use permitted tools.
* Agents return structured results.
* Permissions are enforced.
* Agent failures are recorded.

---

# Phase 3 — Task Engine

## Objective

Create the company's work-management system.

## Hierarchy

```text
PROJECT
 ↓
EPIC
 ↓
TASK
 ↓
SUBTASK
```

## Task properties

Every task must contain:

* ID
* Project ID
* Parent task
* Description
* Requirements
* Dependencies
* Priority
* Assigned agent
* Status
* Attempts
* Timeout
* Inputs
* Outputs
* Errors
* Tests
* Completion criteria

## Scheduler

The scheduler must:

* Find ready tasks.
* Respect dependencies.
* Check resources.
* Select an appropriate agent.
* Start execution.
* Track progress.
* Handle failures.
* Retry within limits.

## Completion Criteria

* Tasks can be created.
* Tasks can be assigned.
* Dependencies work.
* Task states are persistent.
* Scheduler executes ready tasks.
* Failed tasks can retry.
* Blocked tasks are identifiable.

---

# Phase 4 — Master Manager

## Objective

Build the company's central coordinator.

## Responsibilities

The Master Manager must:

* Understand company state.
* Read the mission.
* Create projects.
* Plan projects.
* Create tasks.
* Assign agents.
* Monitor execution.
* Detect failures.
* Trigger quality gates.
* Escalate blocked work.
* Decide project state transitions.

## Architecture

```text
Mission
   ↓
Master Manager
   ↓
Project Plan
   ↓
Task Graph
   ↓
Scheduler
   ↓
Agents
```

## Completion Criteria

The Master Manager can successfully coordinate a small controlled software project from planning through completion.

---

# Phase 5 — Project Engine

## Objective

Create the system that manages complete software projects.

## Project lifecycle

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

## Project Engine responsibilities

* Project creation
* Project metadata
* Requirements
* Architecture
* Task graph
* Project state
* Project memory
* Project repository
* Project artifacts
* Project completion criteria

## Completion Criteria

A project can be created and tracked through every lifecycle state.

---

# Phase 6 — Engineering Agents

## Objective

Add specialized software-development departments.

## Agents

```text
Frontend Engineer
Backend Engineer
AI Engineer
Database Engineer
Infrastructure Engineer
```

## Engineering workflow

```text
Requirement
    ↓
Architecture
    ↓
Task
    ↓
Engineering Agent
    ↓
Code
    ↓
Tests
```

## Important rule

Engineering agents must work through controlled tools.

They must not have unrestricted access to the host machine.

## Completion Criteria

At least one complete software project can be implemented by the engineering agents.

---

# Phase 7 — Sandbox

## Objective

Isolate autonomous software execution.

## Technology

Docker will be the primary isolation mechanism.

## Sandbox responsibilities

* Project workspace
* Dependency isolation
* Process isolation
* Resource limits
* Network restrictions
* Temporary environments
* Test execution
* Cleanup

## Resource controls

* CPU limits
* RAM limits
* Runtime limits
* Process limits
* Disk limits
* Concurrent execution limits

## Completion Criteria

An engineering agent can build and test software inside an isolated environment without unrestricted host access.

---

# Phase 8 — QA + Debugging

## Objective

Make software quality a first-class autonomous process.

## QA Agents

* Unit Test Agent
* Integration Test Agent
* E2E Test Agent
* Regression Test Agent
* Build Validation Agent

## Debugging workflow

```text
Test
 ↓
Failure
 ↓
Error Analysis
 ↓
Hypothesis
 ↓
Fix
 ↓
Retest
```

Maximum retry count must be configurable.

Example:

```text
MAX_RETRIES = 5
```

## Completion Criteria

The system can detect a failing test, analyze the failure, attempt a fix, and retest automatically.

Unresolved failures become `BLOCKED`.

---

# Phase 9 — Security + Code Review

## Objective

Prevent unsafe or low-quality software from reaching release.

## Security checks

* Secret detection
* Dependency scanning
* Authentication
* Authorization
* Input validation
* Injection protection
* XSS
* CSRF
* Unsafe commands
* Container security
* API exposure
* File permissions

## Code Review

The reviewer should ideally be independent from the agent that produced the implementation.

Review areas:

* Requirements
* Architecture
* Correctness
* Security
* Maintainability
* Tests
* Edge cases
* Complexity

## Completion Criteria

A project cannot release until security and code review gates pass.

---

# Phase 10 — GitHub Automation

## Objective

Make GitHub the operational engineering headquarters.

## Capabilities

The system should eventually support:

```text
Create repository
Create branch
Commit
Push
Create issue
Create pull request
Request review
Merge pull request
Create release
```

## GitHub workflow

```text
Task
 ↓
Branch
 ↓
Implementation
 ↓
Tests
 ↓
Commit
 ↓
Push
 ↓
Pull Request
 ↓
Review
 ↓
Quality Gate
 ↓
Merge
 ↓
Release
```

## Security

GitHub actions must use scoped credentials.

Dangerous operations require explicit permission.

## Completion Criteria

The company can autonomously manage a complete software repository lifecycle under controlled permissions.

---

# Phase 11 — Memory + Learning

## Objective

Allow the company to retain useful knowledge between projects.

## Memory types

```text
Project Memory
Company Memory
Technical Memory
Decision Memory
Failure Memory
Agent Performance Memory
```

## Memory pipeline

```text
Project
 ↓
Events
 ↓
Results
 ↓
Analysis
 ↓
Lessons
 ↓
Memory
 ↓
Future Projects
```

## Semantic Memory

A vector database may be introduced for semantic retrieval.

Possible technologies:

* Qdrant
* Chroma

The final choice will be made based on implementation requirements.

## Completion Criteria

The company can retrieve relevant knowledge from previous work when planning or executing future tasks.

---

# Phase 12 — Dashboard

## Objective

Provide complete visibility into the company.

## Main sections

```text
Da
```
