from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock


@dataclass(frozen=True, slots=True)
class MemoryInsight:
    key: str
    value: str
    project_id: str | None = None
    importance: float = 1.0
    created_at: datetime = datetime.now(UTC)


class CrossProjectMemory:
    """Process-wide knowledge index for reusable project insights."""

    def __init__(self) -> None:
        self._items: dict[str, list[MemoryInsight]] = {}
        self._lock = RLock()

    def remember(self, insight: MemoryInsight) -> MemoryInsight:
        with self._lock:
            self._items.setdefault(insight.key, []).append(insight)
        return insight

    def recall(self, key: str, limit: int = 10) -> list[MemoryInsight]:
        if limit < 1:
            return []
        with self._lock:
            return list(reversed(self._items.get(key, [])))[:limit]

    def search(self, text: str, limit: int = 20) -> list[MemoryInsight]:
        needle = text.lower().strip()
        if not needle:
            return []
        with self._lock:
            values = [item for items in self._items.values() for item in items]
        values.sort(key=lambda item: (item.importance, item.created_at), reverse=True)
        return [
            item for item in values
            if needle in item.key.lower() or needle in item.value.lower()
        ][:limit]

    def project_history(self, project_id: str, limit: int = 20) -> list[MemoryInsight]:
        with self._lock:
            values = [
                item for items in self._items.values()
                for item in items
                if item.project_id == project_id
            ]
        values.sort(key=lambda item: item.created_at, reverse=True)
        return values[:limit]
