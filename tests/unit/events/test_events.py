from src.events.models.contracts import CompanyEvent
from src.events.service.service import EventService


def test_event_service_publishes_and_lists_events() -> None:
    service = EventService()
    received = []

    service.subscribe(received.append)

    event = service.publish(
        CompanyEvent(
            event_type="project.started",
            project_id="project-1",
            payload={"name": "demo"},
        )
    )

    assert event.event_type == "project.started"
    assert received == [event]
    assert service.list_events("project-1") == [event]


def test_event_service_filters_by_project() -> None:
    service = EventService()

    service.publish(
        CompanyEvent(
            event_type="project.started",
            project_id="project-1",
        )
    )

    service.publish(
        CompanyEvent(
            event_type="project.started",
            project_id="project-2",
        )
    )

    assert len(service.list_events("project-1")) == 1
