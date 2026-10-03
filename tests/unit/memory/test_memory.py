
from src.memory.models.contracts import (
    MemoryCreateRequest,
    MemorySearchRequest,
)
from src.memory.models.enums import MemoryType
from src.memory.service.service import MemoryService


def test_memory_can_be_saved_and_retrieved() -> None:
    service = MemoryService()

    memory = service.remember(
        MemoryCreateRequest(
            memory_type=MemoryType.TECHNICAL,
            title="Use bounded retries",
            content="Debugging must have a maximum retry count.",
        )
    )

    assert service.get(memory.id) == memory


def test_memory_search_matches_content() -> None:
    service = MemoryService()

    service.remember(
        MemoryCreateRequest(
            memory_type=MemoryType.FAILURE,
            title="Sandbox timeout",
            content="Long-running commands must respect timeout limits.",
        )
    )

    results = service.search(
        MemorySearchRequest(query="timeout")
    )

    assert len(results) == 1
    assert results[0].memory_type == MemoryType.FAILURE


def test_memory_search_filters_by_type_and_project() -> None:
    service = MemoryService()

    service.remember(
        MemoryCreateRequest(
            memory_type=MemoryType.DECISION,
            title="Architecture choice",
            content="Use FastAPI for the control plane.",
            project_id="project-1",
        )
    )

    service.remember(
        MemoryCreateRequest(
            memory_type=MemoryType.FAILURE,
            title="Other issue",
            content="Something failed.",
            project_id="project-2",
        )
    )

    results = service.search(
        MemorySearchRequest(
            query="",
            memory_type=MemoryType.DECISION,
            project_id="project-1",
        )
    )

    assert len(results) == 1
    assert results[0].title == "Architecture choice"
