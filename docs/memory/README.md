# Memory & Context Prevention Layer

The AI Software Company must not depend on model conversation context as its
source of truth.

## Memory layers

- Mission
- Project
- Decision
- Task
- Failure
- Lesson
- Agent
- Execution
- Knowledge

## Prevention rules

1. Important state is persisted outside the model.
2. Agents retrieve relevant memory before acting.
3. Project memory is scoped to its project.
4. Execution memory is scoped to its run.
5. Agent memory is scoped to its agent.
6. Failures and lessons can be reused.
7. Retrieval is selective instead of dumping all memory into prompts.
8. Persistent memory is the source of truth.
9. Memory writes are deterministic and testable.
10. Storage can later migrate without changing the memory contract.

## Current storage

The first implementation uses a JSON-backed persistent store.

This establishes the memory contract before introducing PostgreSQL,
embeddings, vector search, or distributed storage.

## Future

JSON store
    ->
Persistent database
    ->
Hybrid keyword + semantic retrieval
    ->
Long-term autonomous learning
