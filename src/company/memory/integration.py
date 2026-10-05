from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import ContextBuilder
from .models import MemoryEntry, MemoryType
from .store import MemoryStore


@dataclass
class MemoryIntegration:
    store: MemoryStore
    context_builder: ContextBuilder

    @classmethod
    def create(
        cls,
        store: MemoryStore | None = None,
        *,
        max_context_entries: int = 20,
    ) -> MemoryIntegration:
        memory_store = store or MemoryStore()
        return cls(
            store=memory_store,
            context_builder=ContextBuilder(
                memory_store,
                max_entries=max_context_entries,
            ),
        )

    def context(
        self,
        *,
        query: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, object]:
        return self.context_builder.build(
            query=query,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
        )

    def remember(
        self,
        *,
        memory_id: str,
        memory_type: MemoryType,
        title: str,
        content: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        importance: int = 5,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        return self.store.write(
            MemoryEntry(
                memory_id=memory_id,
                memory_type=memory_type,
                title=title,
                content=content,
                project_id=project_id,
                run_id=run_id,
                agent_id=agent_id,
                importance=importance,
                tags=list(tags or []),
                metadata=dict(metadata or {}),
            )
        )

    def remember_mission(
        self,
        *,
        memory_id: str,
        mission: str,
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        return self.remember(
            memory_id=memory_id,
            memory_type=MemoryType.MISSION,
            title="Mission",
            content=mission,
            project_id=project_id,
            importance=10,
            tags=["mission"],
            metadata=metadata,
        )

    def remember_task(
        self,
        *,
        memory_id: str,
        task: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        return self.remember(
            memory_id=memory_id,
            memory_type=MemoryType.TASK,
            title="Task",
            content=task,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            importance=8,
            tags=["task"],
            metadata=metadata,
        )

    def remember_decision(
        self,
        *,
        memory_id: str,
        decision: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        return self.remember(
            memory_id=memory_id,
            memory_type=MemoryType.DECISION,
            title="Decision",
            content=decision,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            importance=9,
            tags=["decision"],
            metadata=metadata,
        )

    def remember_failure(
        self,
        *,
        memory_id: str,
        failure: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        return self.remember(
            memory_id=memory_id,
            memory_type=MemoryType.FAILURE,
            title="Failure",
            content=failure,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            importance=9,
            tags=["failure", "recovery"],
            metadata=metadata,
        )

    def remember_handoff(
        self,
        *,
        memory_id: str,
        handoff: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        return self.remember(
            memory_id=memory_id,
            memory_type=MemoryType.EXECUTION,
            title="Agent Handoff",
            content=handoff,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            importance=8,
            tags=["handoff", "execution"],
            metadata=metadata,
        )

    def record_execution_started(
        self,
        *,
        run_id: str,
        project_id: str | None = None,
        agent_id: str | None = None,
        query: str = "",
    ) -> MemoryEntry:
        return self.remember(
            memory_id=f"execution:{run_id}:started",
            memory_type=MemoryType.EXECUTION,
            title="Execution Started",
            content=query or f"Autonomous execution {run_id} started.",
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            importance=6,
            tags=["execution", "started"],
        )

    def record_execution_completed(
        self,
        *,
        run_id: str,
        result: Any,
        project_id: str | None = None,
        agent_id: str | None = None,
    ) -> MemoryEntry:
        return self.remember(
            memory_id=f"execution:{run_id}:completed",
            memory_type=MemoryType.EXECUTION,
            title="Execution Completed",
            content=f"Autonomous execution {run_id} completed successfully.",
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            importance=7,
            tags=["execution", "completed"],
            metadata={"result": repr(result)},
        )

    def record_execution_failed(
        self,
        *,
        run_id: str,
        error: str,
        project_id: str | None = None,
        agent_id: str | None = None,
    ) -> MemoryEntry:
        return self.remember_failure(
            memory_id=f"execution:{run_id}:failed",
            failure=error,
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
            metadata={"execution_run_id": run_id},
        )
