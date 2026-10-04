from src.events.models.contracts import CompanyEvent
from src.events.service.service import EventService


def test_company_event_contains_memory_ready_context() -> None:
    service = EventService()

    event = service.publish(
        CompanyEvent(
            event_type="qa.failed",
            project_id="project-1",
            task_id="task-1",
            agent_name="backend-engineer",
            payload={
                "error": "test failed",
                "attempt": 1,
            },
        )
    )

    assert event.project_id == "project-1"
    assert event.task_id == "task-1"
    assert event.agent_name == "backend-engineer"
    assert event.payload["attempt"] == 1
