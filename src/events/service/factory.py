from src.events.service.service import EventService

_event_service = EventService()


def get_event_service() -> EventService:
    return _event_service
