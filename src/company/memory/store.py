from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from .models import MemoryEntry, MemoryType


class MemoryStore:
    def __init__(self, path: str | Path = "data/memory.json") -> None:
        self.path = Path(path)
        self._lock = Lock()
        self._entries: dict[str, MemoryEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return

        data = json.loads(self.path.read_text(encoding="utf-8"))

        for item in data:
            entry = MemoryEntry(
                memory_id=item["memory_id"],
                memory_type=MemoryType(item["memory_type"]),
                title=item["title"],
                content=item["content"],
                project_id=item.get("project_id"),
                run_id=item.get("run_id"),
                agent_id=item.get("agent_id"),
                importance=item.get("importance", 5),
                tags=item.get("tags", []),
                metadata=item.get("metadata", {}),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )
            self._entries[entry.memory_id] = entry

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        payload = [
            {
                "memory_id": entry.memory_id,
                "memory_type": entry.memory_type.value,
                "title": entry.title,
                "content": entry.content,
                "project_id": entry.project_id,
                "run_id": entry.run_id,
                "agent_id": entry.agent_id,
                "importance": entry.importance,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            }
            for entry in self._entries.values()
        ]

        self.path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def write(self, entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            self._entries[entry.memory_id] = entry
            self._save()
        return entry

    def get(self, memory_id: str) -> MemoryEntry:
        if memory_id not in self._entries:
            raise KeyError(memory_id)
        return self._entries[memory_id]

    def delete(self, memory_id: str) -> None:
        with self._lock:
            if memory_id not in self._entries:
                raise KeyError(memory_id)
            del self._entries[memory_id]
            self._save()

    def list(
        self,
        *,
        memory_type: MemoryType | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        tags: list[str] | None = None,
    ) -> list[MemoryEntry]:
        requested_tags = set(tags or [])
        entries = list(self._entries.values())

        if memory_type is not None:
            entries = [e for e in entries if e.memory_type == memory_type]

        if project_id is not None:
            entries = [e for e in entries if e.project_id == project_id]

        if run_id is not None:
            entries = [e for e in entries if e.run_id == run_id]

        if agent_id is not None:
            entries = [e for e in entries if e.agent_id == agent_id]

        if requested_tags:
            entries = [
                e
                for e in entries
                if requested_tags.intersection(e.tags)
            ]

        return sorted(
            entries,
            key=lambda entry: (
                entry.importance,
                entry.updated_at,
            ),
            reverse=True,
        )

    def search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        terms = {
            term.lower()
            for term in query.split()
            if term.strip()
        }

        candidates = self.list(project_id=project_id)
        scored: list[tuple[int, MemoryEntry]] = []

        for entry in candidates:
            haystack = " ".join(
                [entry.title, entry.content, *entry.tags]
            ).lower()

            score = sum(term in haystack for term in terms)

            if score:
                scored.append((score, entry))

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].importance,
                item[1].updated_at,
            ),
            reverse=True,
        )

        return [entry for _, entry in scored[:limit]]

    def count(self) -> int:
        return len(self._entries)

    def export(self) -> list[dict[str, Any]]:
        return [
            {
                "memory_id": entry.memory_id,
                "memory_type": entry.memory_type.value,
                "title": entry.title,
                "content": entry.content,
                "project_id": entry.project_id,
                "run_id": entry.run_id,
                "agent_id": entry.agent_id,
                "importance": entry.importance,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            }
            for entry in self._entries.values()
        ]
