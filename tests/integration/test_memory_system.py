from company.memory import (
    ContextBuilder,
    MemoryEntry,
    MemoryStore,
    MemoryType,
)


def test_memory_persists(tmp_path):
    path = tmp_path / "memory.json"
    store = MemoryStore(path)

    entry = MemoryEntry(
        memory_id="decision-1",
        memory_type=MemoryType.DECISION,
        title="Architecture decision",
        content="Use persistent memory for autonomous context.",
        project_id="ai-company",
        importance=10,
        tags=["architecture", "memory"],
    )

    store.write(entry)

    restored = MemoryStore(path)
    result = restored.get(entry.memory_id)

    assert result.content == entry.content
    assert result.project_id == "ai-company"
    assert result.importance == 10


def test_memory_search(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")

    store.write(
        MemoryEntry(
            memory_id="memory-1",
            memory_type=MemoryType.LESSON,
            title="Context retention",
            content="Agents must retrieve persistent project context.",
            importance=9,
            tags=["context", "agents"],
        )
    )

    store.write(
        MemoryEntry(
            memory_id="memory-2",
            memory_type=MemoryType.KNOWLEDGE,
            title="Unrelated",
            content="Database indexing information.",
            importance=5,
        )
    )

    results = store.search("persistent context agents")

    assert results
    assert results[0].memory_id == "memory-1"


def test_context_builder(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")

    store.write(
        MemoryEntry(
            memory_id="project-memory",
            memory_type=MemoryType.PROJECT,
            title="Project architecture",
            content="The project uses an autonomous runtime.",
            project_id="project-1",
            importance=10,
        )
    )

    store.write(
        MemoryEntry(
            memory_id="run-memory",
            memory_type=MemoryType.EXECUTION,
            title="Current execution",
            content="The current run is testing memory retrieval.",
            project_id="project-1",
            run_id="run-1",
            importance=8,
        )
    )

    context = ContextBuilder(store).build(
        query="autonomous runtime",
        project_id="project-1",
        run_id="run-1",
    )

    ids = {item["memory_id"] for item in context["memories"]}

    assert "project-memory" in ids
    assert "run-memory" in ids


def test_memory_delete(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")

    store.write(
        MemoryEntry(
            memory_id="delete-me",
            memory_type=MemoryType.TASK,
            title="Temporary task",
            content="Temporary context",
        )
    )

    store.delete("delete-me")

    assert store.count() == 0


def test_memory_filters(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")

    store.write(
        MemoryEntry(
            memory_id="project-a",
            memory_type=MemoryType.PROJECT,
            title="A",
            content="Project A",
            project_id="a",
            tags=["important"],
        )
    )

    store.write(
        MemoryEntry(
            memory_id="project-b",
            memory_type=MemoryType.PROJECT,
            title="B",
            content="Project B",
            project_id="b",
            tags=["other"],
        )
    )

    results = store.list(
        memory_type=MemoryType.PROJECT,
        project_id="a",
        tags=["important"],
    )

    assert len(results) == 1
    assert results[0].memory_id == "project-a"
