# M61 — Real Project Execution

M61 provides the autonomous company with a controlled execution workspace.

## Capabilities

- isolated temporary workspace per project
- safe file creation, reading, listing and deletion
- workspace traversal protection
- integration with the existing sandbox executor
- bounded command execution
- stdout/stderr/exit-code capture
- timeout reporting
- test execution
- build execution
- fail-fast execution
- artifact discovery
- artifact size/count limits
- explicit workspace cleanup

## Execution Flow

```text
Factory Project
      |
      v
ProjectExecutionService
      |
      v
Isolated ProjectWorkspace
      |
      +---- Files
      |
      +---- Tests
      |
      +---- Build
      |
      v
Artifact Collection
      |
      v
Execution Result
