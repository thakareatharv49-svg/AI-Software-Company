from src.memory.models.contracts import (
    MemoryCreateRequest,
    MemoryEntry,
    MemorySearchRequest,
)
from src.memory.models.enums import MemoryType
from src.memory.store.memory import InMemoryMemoryStore


class MemoryService:
    def __init__(
        self,
        store: InMemoryMemoryStore | None = None,
    ) -> None:
        self.store = store or InMemoryMemoryStore()

    def remember(self, request: MemoryCreateRequest) -> MemoryEntry:
        return self.store.save(request)

    def get(self, memory_id: str) -> MemoryEntry | None:
        return self.store.get(memory_id)

    def search(self, request: MemorySearchRequest) -> list[MemoryEntry]:
        results = self.store.search(request.query)

        if request.memory_type is not None:
            results = [
                memory
                for memory in results
                if memory.memory_type == request.memory_type
            ]

        if request.project_id is not None:
            results = [
                memory
                for memory in results
                if memory.project_id == request.project_id
            ]

        return results[: request.limit]

    def list_by_type(
        self,
        memory_type: MemoryType,
    ) -> list[MemoryEntry]:
        return self.store.filter(memory_type=memory_type)
