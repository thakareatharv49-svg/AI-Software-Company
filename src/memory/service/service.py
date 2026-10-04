from src.events.models.contracts import CompanyEvent
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

    def remember_event(
        self,
        event: CompanyEvent,
    ) -> None:
        try:
            from src.memory.models.contracts import MemoryCreateRequest
            from src.memory.models.enums import MemoryType

            request = MemoryCreateRequest(
                memory_type=MemoryType.EVENT,
                content=(
                    f"Event: {event.event_type}. "
                    f"Project: {event.project_id or 'unknown'}. "
                    f"Task: {event.task_id or 'unknown'}. "
                    f"Agent: {event.agent_name or 'unknown'}. "
                    f"Payload: {event.payload}"
                ),
                metadata={
                    "event_type": event.event_type,
                    "project_id": event.project_id,
                    "task_id": event.task_id,
                    "agent_name": event.agent_name,
                },
            )

            self.create(request)
        except Exception:
            return None
