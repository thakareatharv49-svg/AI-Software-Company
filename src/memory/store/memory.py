from src.memory.models.contracts import MemoryCreateRequest, MemoryEntry
from src.memory.models.enums import MemoryType
from src.memory.store.base import MemoryStore


class InMemoryMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self._memories: dict[str, MemoryEntry] = {}

    def save(self, request: MemoryCreateRequest) -> MemoryEntry:
        memory = MemoryEntry(**request.model_dump())
        self._memories[memory.id] = memory
        return memory

    def get(self, memory_id: str) -> MemoryEntry | None:
        return self._memories.get(memory_id)

    def list_all(self) -> list[MemoryEntry]:
        return list(self._memories.values())

    def search(self, query: str) -> list[MemoryEntry]:
        normalized = query.strip().lower()

        if not normalized:
            return self.list_all()

        results: list[MemoryEntry] = []

        for memory in self._memories.values():
            searchable = " ".join(
                [
                    memory.title,
                    memory.content,
                    memory.memory_type.value,
                    memory.agent_name or "",
                    memory.project_id or "",
                    " ".join(memory.tags),
                ]
            ).lower()

            if normalized in searchable:
                results.append(memory)

        return results

    def filter(
        self,
        *,
        memory_type: MemoryType | None = None,
        project_id: str | None = None,
    ) -> list[MemoryEntry]:
        return [
            memory
            for memory in self._memories.values()
            if (
                memory_type is None
                or memory.memory_type == memory_type
            )
            and (
                project_id is None
                or memory.project_id == project_id
            )
        ]
