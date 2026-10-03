# AI Software Company — System Architecture

## 1. Purpose

This document defines the executable architecture of the AI Software Company.

The architecture is designed around six fundamental concepts:

```text
Model
  ↓
Agent
  ↓
Tool
  ↓
Task
  ↓
Project
  ↓
Manager
```

Supporting all of them are:

```text
Events
Memory
Database
Sandbox
GitHub
Quality Gates
Observability
```

---

# 2. High-Level Architecture

```text
                         HUMAN
                           │
                           ▼
                  ┌─────────────────┐
                  │ MASTER MANAGER  │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        PROJECT ENGINE  TASK ENGINE  RESOURCE MANAGER
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    AGENT RUNTIME
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           MODEL         TOOLS       MEMORY
              │            │            │
              └────────────┼────────────┘
                           ▼
                        SANDBOX
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
             CODE        TESTS        GITHUB
              │            │            │
              └────────────┼────────────┘
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

# 3. Core Components

## 3.1 Master Manager

The Master Manager is the central coordinator.

Responsibilities:

* Interpret mission
* Maintain company state
* Select projects
* Create project plans
* Create tasks
* Assign agents
* Monitor execution
* Handle blocked work
* Trigger quality gates
* Coordinate releases
* Record decisions
* Start future projects

The Manager should not directly implement most software tasks.

---

# 4. Agent Runtime

The Agent Runtime provides a common execution environment.

```text
Agent Definition
      ↓
Agent Context
      ↓
Model
      ↓
Tool Selection
      ↓
Tool Execution
      ↓
Result
```

Each execution should have:

* Agent ID
* Task ID
* Project ID
* Model ID
* Start time
* End time
* Tool calls
* Result
* Errors
* Token/resource information where available

---

# 5. Model Layer

The Model Layer abstracts AI providers.

```text
Model Interface
      │
 ┌────┼──────────────┐
 ▼    ▼              ▼
Ollama Future Local  Optional External
```

The rest of the system must not depend directly on a specific model provider.

Example interface:

```text
generate()
stream()
health_check()
list_models()
```

---

# 6. Model Router

The Model Router selects an appropriate model for a task.

Inputs:

* Task type
* Complexity
* Required capabilities
* Context size
* Available RAM
* CPU availability
* Current queue
* Model availability

Example:

```text
Simple task
   ↓
Small model

Coding task
   ↓
Coding-capable model

Architecture task
   ↓
Stronger reasoning model
```

The router must avoid using expensive resources unnecessarily.

---

# 7. Agent Registry

The Agent Registry stores available agents.

Each agent has:

```text
ID
Name
Role
Capabilities
Tools
Permissions
Model
Limits
Status
Version
```

Example:

```yaml
agent:
  id: backend_engineer
  role: backend development

  capabilities:
    - python
    - fastapi
    - postgresql

  tools:
    - filesystem
    - terminal
    - git
    - testing

  permissions:
    filesystem:
      read: project
      write: project

    terminal:
      allowed: project_commands

  limits:
    max_runtime: 1800
    max_retries: 5
```

---

# 8. Tool System

Tools are controlled interfaces between agents and the environment.

Initial tool categories:

```text
Filesystem
Terminal
Git
GitHub
Docker
Testing
Research
```

Each tool must define:

* Name
* Version
* Input schema
* Output schema
* Permissions
* Risk level
* Timeout
* Audit behavior

---

# 9. Permission System

Every tool execution passes through permission checking.

```text
Agent
  ↓
Requested Tool
  ↓
Permission Check
  ↓
Allowed?
 ┌───────┴───────┐
 YES             NO
  ↓               ↓
Execute         Reject
```

The permission system should follow least privilege.

---

# 10. Task Engine

The Task Engine manages executable work.

Task hierarchy:

```text
Project
  ↓
Epic
  ↓
Task
  ↓
Subtask
```

Task dependencies form a directed graph.

Example:

```text
Database Schema
      ↓
Backend API
      ↓
Authentication
      ↓
Frontend Integration
      ↓
E2E Tests
```

A task cannot start until required dependencies are satisfied.

---

# 11. Scheduler

The Scheduler decides which ready task should run.

Inputs:

* Task priority
* Dependencies
* Agent availability
* Resource availability
* Task requirements
* Project priority
* Retry state

The scheduler must prevent resource exhaustion.

---

# 12. Project Engine

Projects are the main unit of autonomous work.

Each project contains:

```text
Project
├── Requirements
├── Product Definition
├── Architecture
├── Tasks
├── Repository
├── Agents
├── Tests
├── Security
├── Reviews
├── Releases
├── Decisions
├── Logs
└── Memory
```

---

# 13. Project State Machine

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

State transitions must be validated by the state machine.

---

# 14. Event Bus

The Event Bus connects system components.

Example:

```text
TASK_COMPLETED
      ↓
Event Bus
      ↓
Scheduler
      ↓
Check Dependencies
      ↓
Start Newly Ready Tasks
```

Important events:

```text
PROJECT_CREATED
PROJECT_STATE_CHANGED

TASK_CREATED
TASK_STARTED
TASK_COMPLETED
TASK_FAILED
TASK_BLOCKED

AGENT_STARTED
AGENT_COMPLETED
AGENT_FAILED

TEST_STARTED
TEST_FAILED
TEST_PASSED

SECURITY_FAILED
REVIEW_REQUESTED
REVIEW_FAILED

PR_CREATED
PR_MERGED
RELEASE_CREATED

PROJECT_COMPLETED
```

---

# 15. Database

PostgreSQL is the primary structured database.

Initial entities:

```text
users
companies
projects
project_requirements
project_decisions
agents
agent_runs
tasks
task_dependencies
tool_definitions
tool_calls
events
test_runs
security_scans
code_reviews
repositories
pull_requests
releases
memory_entries
resources
audit_logs
```

The database should store state and metadata.

Large artifacts such as source repositories should remain in Git.

---

# 16. Initial Entity Relationships

```text
COMPANY
  │
  ├── PROJECT
  │      │
  │      ├── REQUIREMENTS
  │      ├── TASKS
  │      ├── DECISIONS
  │      ├── TESTS
  │      ├── SECURITY
  │      ├── REVIEWS
  │      ├── RELEASES
  │      └── MEMORY
  │
  └── AGENTS
          │
          └── AGENT RUNS
```

Tasks connect projects and agents:

```text
PROJECT
   ↓
TASK
   ↓
AGENT
   ↓
AGENT RUN
   ↓
TOOL CALLS
```

---

# 17. Audit Log

Important actions must be auditable.

Each audit record should contain:

```text
ID
Timestamp
Actor
Actor Type
Action
Resource
Resource ID
Input Summary
Result
Risk Level
Success/Failure
```

Example:

```text
agent/backend_engineer
ACTION: git.push
REPOSITORY: project-x
RESULT: SUCCESS
```

Sensitive information must not be written into logs.

---

# 18. Memory Architecture

Memory has four primary layers:

```text
Project Memory
      │
      ▼
Technical Memory
      │
      ▼
Company Memory
      │
      ▼
Semantic Retrieval
```

Structured facts belong in PostgreSQL.

Semantic knowledge may use:

* Qdrant
* Chroma
* another compatible vector store

The implementation will begin with the simplest reliable design.

---

# 19. Sandbox Architecture

The Sandbox isolates project execution.

```text
Host
 │
 └── Company Runtime
       │
       └── Docker
             │
             └── Project Container
                    ├── Source
                    ├── Dependencies
                    ├── Tests
                    └── Build
```

Agents interact with the project container through controlled tools.

---

# 20. Git Architecture

Git is the source-control layer.

Each project should normally have its own repository.

Typical workflow:

```text
main
 │
 ├── feature/task-123
 │
 ├── feature/task-124
 │
 └── fix/task-125
```

Engineering agents work on task-specific branches where practical.

---

# 21. GitHub Architecture

GitHub provides remote collaboration and release infrastructure.

```text
Local Repository
      ↓
Git
      ↓
GitHub Repository
      ↓
Pull Request
      ↓
CI
      ↓
Review
      ↓
Quality Gate
      ↓
Merge
      ↓
Release
```

The company should use a controlled GitHub abstraction instead of giving agents unrestricted GitHub CLI access.

---

# 22. Quality Gate Architecture

The Quality Gate aggregates results from:

```text
Requirements
Architecture
Tests
Security
Code Review
Documentation
Build
Deployment
GitHub
```

Example:

```text
             QUALITY GATE
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
     Tests     Security    Review
       │          │          │
       └──────────┼──────────┘
                  ▼
              DECISION
             /        \
          PASS        FAIL
           ↓            ↓
        Release      Block
```

---

# 23. Resource Manager

The Resource Manager controls system capacity.

Resources include:

* CPU
* RAM
* Disk
* Model availability
* Agent concurrency
* Docker containers

Example:

```text
Available RAM: 8 GB
Running Agents: 1
Queued Tasks: 7
```

The scheduler must respect resource limits.

---

# 24. Observability

The system should expose:

```text
Metrics
Logs
Events
Traces
Audit Records
```

Important metrics:

* Task duration
* Agent duration
* Test duration
* Failure rate
* Retry rate
* Resource usage
* Project completion time
* Model usage
* Tool failure rate

---

# 25. Dashboard Architecture

The dashboard communicates with the backend through APIs.

```text
React / Next.js
      ↓
FastAPI
      ↓
Company Services
      ↓
PostgreSQL
```

The dashboard should never directly modify internal database state.

All mutations should pass through backend services and permission checks.

---

# 26. Service Boundaries

Initial backend services:

```text
Company Service
Project Service
Task Service
Agent Service
Tool Service
GitHub Service
Memory Service
Quality Service
Audit Service
Resource Service
```

Initially these can exist inside one modular application.

A microservice architecture is not required at the beginning.

---

# 27. Recommended Initial Architecture

Start as a modular monolith.

```text
FastAPI Application
│
├── company/
├── projects/
├── tasks/
├── agents/
├── tools/
├── models/
├── memory/
├── github/
├── quality/
├── security/
├── resources/
├── events/
└── audit/
```

Benefits:

* Easier development
* Lower resource consumption
* Easier debugging
* Fewer distributed-system problems
* Easier local deployment

The architecture can be split into services later if required.

---

# 28. Execution Flow

A normal task execution:

```text
1. Scheduler finds READY task
2. Resource Manager checks capacity
3. Agent Registry selects capable agent
4. Model Router selects model
5. Agent receives task context
6. Agent requests tool
7. Permission system validates request
8. Tool executes
9. Result returns to agent
10. Agent produces result
11. Task state updates
12. Event emitted
13. Audit record created
14. Dependent tasks become eligible
```

---

# 29. Failure Flow

```text
Task
 ↓
Agent
 ↓
Tool Failure
 ↓
Agent Analysis
 ↓
Retry
 ↓
Success
```

If retry limit is reached:

```text
Task
 ↓
FAILED
 ↓
BLOCKED
 ↓
Manager
 ↓
Decision
```

---

# 30. First Implementation Boundary

The first executable version will contain only:

```text
FastAPI
PostgreSQL
Configuration
Logging
AI Runtime
One Agent
Tool Registry
One Safe Tool
Task Model
Basic Scheduler
Tests
```

It will NOT initially contain:

* 20 agents
* Complex distributed services
* Full dashboard
* Autonomous project discovery
* Self-modifying code
* Multi-machine orchestration

Complexity will be introduced only after the foundation is reliable.

---

# 31. Architectural Principles

1. Least privilege
2. Explicit state
3. Reproducibility
4. Testability
5. Observability
6. Modular design
7. Controlled autonomy
8. Meaningful Git history
9. Human override
10. Failure containment
11. Resource awareness
12. Security by default
13. Open-source-first
14. Avoid unnecessary complexity

---

# 32. Architectural Evolution

The architecture should evolve in stages:

```text
Modular Monolith
      ↓
Reliable Agent Runtime
      ↓
Reliable Autonomous Projects
      ↓
Optional Service Separation
      ↓
Distributed Execution
      ↓
Multi-Machine Company
```

The system should not introduce distributed complexity before it provides practical value.
