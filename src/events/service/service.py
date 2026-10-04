from collections.abc import Callable

from src.events.models.contracts import CompanyEvent


class EventService:
    def __init__(self) -> None:
        self._events: list[CompanyEvent] = []
        self._subscribers: list[Callable[[CompanyEvent], None]] = []

    def publish(self, event: CompanyEvent) -> CompanyEvent:
        self._events.append(event)
        for subscriber in self._subscribers:
            subscriber(event)
        return event

    def subscribe(
        self,
        subscriber: Callable[[CompanyEvent], None],
    ) -> None:
        self._subscribers.append(subscriber)

    def list_events(
        self,
        project_id: str | None = None,
    ) -> list[CompanyEvent]:
        if project_id is None:
            return list(self._events)

        return [
            event
            for event in self._events
            if event.project_id == project_id
        ]

    def clear(self) -> None:
        self._events.clear()
