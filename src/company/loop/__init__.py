from src.company.loop.concurrency import ConcurrentProjectRunner, ProjectRunResult
from src.company.loop.discovery import Opportunity, OpportunityDiscovery
from src.company.loop.lifecycle import LifecycleState, ProjectLifecycle


class HealingAction:
    def __init__(self, project_id, action, attempt, success, reason):
        self.project_id = project_id
        self.action = action
        self.attempt = attempt
        self.success = success
        self.reason = reason


class SelfHealingService:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self._attempts = {}
        self._history = []

    async def heal(self, project_id, operation):
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
            action = HealingAction(project_id, "retry", attempt, False, str(exc))
        else:
            action = HealingAction(
                project_id,
                "retry",
                attempt,
                True,
                "Recovery succeeded.",
            )
            self._attempts.pop(project_id, None)
        self._history.append(action)
        return action

    def history(self):
        return list(self._history)


__all__ = [
    "LifecycleState",
    "ProjectLifecycle",
    "ConcurrentProjectRunner",
    "ProjectRunResult",
    "HealingAction",
    "SelfHealingService",
    "Opportunity",
    "OpportunityDiscovery",
    "CompanyOperatingLoop",
]
