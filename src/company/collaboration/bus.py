from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class CollaborationMessage:
    sender: str
    recipient: str
    content: str
    message_type: str = "message"
    context: dict[str, object] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class Handoff:
    task_id: str
    sender: str
    recipient: str
    context: dict[str, object] = field(default_factory=dict)
    status: str = "pending"


class CollaborationBus:
    """Deterministic message and handoff boundary for agents."""

    def __init__(self) -> None:
        self._messages: list[CollaborationMessage] = []
        self._handoffs: list[Handoff] = []

    def send(self, message: CollaborationMessage) -> None:
        if not message.sender.strip() or not message.recipient.strip():
            raise ValueError("sender and recipient are required")
        self._messages.append(message)

    def messages(self, *, recipient: str | None = None) -> tuple[CollaborationMessage, ...]:
        items = self._messages
        if recipient is not None:
            items = [item for item in items if item.recipient == recipient]
        return tuple(items)

    def handoff(self, handoff: Handoff) -> None:
        if not handoff.task_id.strip():
            raise ValueError("task_id is required")
        self._handoffs.append(handoff)

    def handoffs(self, *, recipient: str | None = None) -> tuple[Handoff, ...]:
        items = self._handoffs
        if recipient is not None:
            items = [item for item in items if item.recipient == recipient]
        return tuple(items)

    def synchronize(self, agent: str) -> dict[str, object]:
        return {
            "agent": agent,
            "messages": self.messages(recipient=agent),
            "handoffs": self.handoffs(recipient=agent),
        }
