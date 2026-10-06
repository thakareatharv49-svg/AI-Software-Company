from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LifecycleState(StrEnum):
    DISCOVERED = "discovered"
    PLANNED = "planned"
    EXECUTING = "executing"
    VALIDATING = "validating"
    RELEASED = "released"
    FAILED = "failed"
    RECOVERING = "recovering"


_ALLOWED: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.DISCOVERED: frozenset({LifecycleState.PLANNED, LifecycleState.FAILED}),
    LifecycleState.PLANNED: frozenset({LifecycleState.EXECUTING, LifecycleState.FAILED}),
    LifecycleState.EXECUTING: frozenset({LifecycleState.VALIDATING, LifecycleState.FAILED}),
    LifecycleState.VALIDATING: frozenset({LifecycleState.RELEASED, LifecycleState.FAILED}),
    LifecycleState.RELEASED: frozenset(),
    LifecycleState.FAILED: frozenset({LifecycleState.RECOVERING}),
    LifecycleState.RECOVERING: frozenset({LifecycleState.PLANNED, LifecycleState.FAILED}),
}


@dataclass(slots=True)
class ProjectLifecycle:
    project_id: str
    state: LifecycleState = LifecycleState.DISCOVERED

    def transition(self, target: LifecycleState) -> LifecycleState:
        if target not in _ALLOWED[self.state]:
            raise ValueError(f"Invalid lifecycle transition: {self.state} -> {target}")
        self.state = target
        return self.state
