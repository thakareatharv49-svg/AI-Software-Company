from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RefactoringPlan:
    target: str
    steps: tuple[str, ...]


class RefactoringService:
    """Creates conservative, reviewable refactoring plans without mutating code implicitly."""

    def plan(self, target: str) -> RefactoringPlan:
        target = target.strip()
        if not target:
            raise ValueError("target must not be empty")
        return RefactoringPlan(
            target,
            ("baseline tests", "make one focused change", "run tests", "review diff"),
        )
