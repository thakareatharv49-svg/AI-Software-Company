from src.company.events.events import CompanyEvent


class CompanyEventBus:
    def __init__(self) -> None:
        self._events: list[CompanyEvent] = []

    def publish(self, event: CompanyEvent) -> None:
        self._events.append(event)

    def list_events(self) -> list[CompanyEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
