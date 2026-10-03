from abc import ABC, abstractmethod

from src.memory.models.contracts import MemoryCreateRequest, MemoryEntry


class MemoryStore(ABC):
    @abstractmethod
    def save(self, request: MemoryCreateRequest) -> MemoryEntry:
        raise NotImplementedError

    @abstractmethod
    def get(self, memory_id: str) -> MemoryEntry | None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[MemoryEntry]:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str) -> list[MemoryEntry]:
        raise NotImplementedError
