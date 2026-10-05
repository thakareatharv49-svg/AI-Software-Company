from __future__ import annotations

from company.memory import MemoryIntegration, MemoryStore, MemoryType
from company.runtime.end_to_end import AutonomousExecution


def test_memory_integration_persists_execution(tmp_path):
    store = MemoryStore(tmp_path / "memory.json")
    memory = MemoryIntegration.create(store)

    memory.record_execution_started(
        run_id="run-1",
        project_id="project-1",
        agent_id="agent-1",
        query="build authentication",
    )

    reloaded = MemoryStore(tmp_path / "memory.json")
    entry = reloaded.get("execution:run-1:started")

    assert entry.memory_type == MemoryType.EXECUTION
    assert entry.project_id == "project-1"
    assert entry.run_id == "run-1"
    assert entry.agent_id == "agent-1"


def test_memory_integration_records_company_knowledge(tmp_path):
    memory = MemoryIntegration.create(
        MemoryStore(tmp_path / "memory.json")
    )

    memory.remember_mission(
        memory_id="mission-1",
        mission="Build an autonomous software company.",
        project_id="project-1",
    )

    memory.remember_task(
        memory_id="task-1",
        task="Implement runtime memory integration.",
        project_id="project-1",
        run_id="run-1",
        agent_id="engineer-1",
    )

    memory.remember_decision(
        memory_id="decision-1",
        decision="Use persistent memory before execution.",
        project_id="project-1",
    )

    memory.remember_handoff(
        memory_id="handoff-1",
        handoff="Engineer completed runtime integration and handed QA the task.",
        project_id="project-1",
        run_id="run-1",
        agent_id="engineer-1",
    )

    assert memory.store.count() == 4


def test_context_retrieval_is_project_scoped(tmp_path):
    memory = MemoryIntegration.create(
        MemoryStore(tmp_path / "memory.json")
    )

    memory.remember_mission(
        memory_id="p1",
        mission="Build project one.",
        project_id="project-1",
    )

    memory.remember_mission(
        memory_id="p2",
        mission="Build project two.",
        project_id="project-2",
    )

    context = memory.context(
        query="Build project",
        project_id="project-1",
    )

    ids = {
        item["memory_id"]
        for item in context["memories"]
    }

    assert "p1" in ids
    assert "p2" not in ids


def test_failure_memory_is_retrievable(tmp_path):
    memory = MemoryIntegration.create(
        MemoryStore(tmp_path / "memory.json")
    )

    memory.record_execution_failed(
        run_id="run-failure",
        error="dependency installation failed",
        project_id="project-1",
    )

    context = memory.context(
        query="dependency installation failed",
        project_id="project-1",
    )

    assert context["memory_count"] >= 1
    assert any(
        item["type"] == "failure"
        for item in context["memories"]
    )


def test_autonomous_execution_writes_memory(tmp_path):
    runtime = AutonomousExecution(
        memory_store=MemoryStore(tmp_path / "memory.json"),
    )

    result = runtime.run(
        "memory-run",
        lambda: {"ok": True},
        project_id="project-1",
        agent_id="agent-1",
        context_query="execute memory integration",
    )

    assert result.status == "completed"
    assert result.context is not None

    started = runtime.memory.store.get(
        "execution:memory-run:started"
    )

    completed = runtime.memory.store.get(
        "execution:memory-run:completed"
    )

    assert started.project_id == "project-1"
    assert completed.agent_id == "agent-1"


def test_autonomous_execution_writes_failure_memory(tmp_path):
    runtime = AutonomousExecution(
        memory_store=MemoryStore(tmp_path / "memory.json"),
    )

    result = runtime.run(
        "memory-failure",
        lambda: (_ for _ in ()).throw(
            RuntimeError("known failure")
        ),
    )

    assert result.status == "failed"

    failures = runtime.memory.store.list(
        memory_type=MemoryType.FAILURE,
        run_id="memory-failure",
    )

    assert failures
    assert "known failure" in failures[0].content


def test_memory_context_survives_runtime_restart(tmp_path):
    path = tmp_path / "memory.json"

    first = AutonomousExecution(
        memory_store=MemoryStore(path),
    )

    first.run(
        "persistent-run",
        lambda: "done",
        project_id="project-restart",
        context_query="persistent execution",
    )

    second = AutonomousExecution(
        memory_store=MemoryStore(path),
    )

    context = second.build_context(
        query="persistent execution",
        project_id="project-restart",
    )

    assert any(
        item["run_id"] == "persistent-run"
        for item in context["memories"]
    )
