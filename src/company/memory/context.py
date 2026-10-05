from __future__ import annotations

from dataclasses import dataclass

from .store import MemoryStore


@dataclass
class ContextBuilder:
    store: MemoryStore
    max_entries: int = 20

    def build(
        self,
        *,
        query: str,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
    ) -> dict[str, object]:
        memories = self.store.search(
            query,
            project_id=project_id,
            limit=self.max_entries,
        )

        scoped = self.store.list(
            project_id=project_id,
            run_id=run_id,
            agent_id=agent_id,
        )

        seen = {entry.memory_id for entry in memories}

        for entry in scoped:
            if entry.memory_id not in seen:
                memories.append(entry)
                seen.add(entry.memory_id)

        memories = sorted(
            memories,
            key=lambda entry: (
                entry.importance,
                entry.updated_at,
            ),
            reverse=True,
        )[: self.max_entries]

        return {
            "query": query,
            "project_id": project_id,
            "run_id": run_id,
            "agent_id": agent_id,
            "memories": [
                {
                    "memory_id": entry.memory_id,
                    "type": entry.memory_type.value,
                    "title": entry.title,
                    "content": entry.content,
                    "project_id": entry.project_id,
                    "run_id": entry.run_id,
                    "agent_id": entry.agent_id,
                    "importance": entry.importance,
                    "tags": list(entry.tags),
                    "metadata": dict(entry.metadata),
                    "created_at": entry.created_at,
                    "updated_at": entry.updated_at,
                }
                for entry in memories
            ],
            "memory_count": len(memories),
        }
