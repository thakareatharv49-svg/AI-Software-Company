from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealingAction:
    project_id: str
    action: str
    attempt: int
    success: bool
    reason: str


class SelfHealingService:
    """Applies bounded recovery strategies without hiding terminal failures."""

    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.max_attempts = max_attempts
        self._attempts: dict[str, int] = {}
        self._history: list[HealingAction] = []

    async def heal(self, project_id: str, operation) -> HealingAction:
        attempt = self._attempts.get(project_id, 0) + 1
        if attempt > self.max_attempts:
            action = HealingAction(
                project_id,
                "blocked",
                attempt,
                False,
                "Maximum recovery attempts reached.",
            )
            self._history.append(action)
            return action

        self._attempts[project_id] = attempt
        try:
            await operation()
        except Exception as exc:
            action = HealingAction("".join([project_id]), "retry", attempt, False, str(exc))
        else:
            action = HealingAction(project_id, "retry", attempt, True, "Recovery succeeded.")
            self._attempts.pop(project_id, None)
        self._history.append(action)
        return action

    def history(self) -> list[HealingAction]:
        return list(self._history)
