from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    max_cost: float
    max_tokens: int | None = None
    max_runtime_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ResourceUsage:
    cost: float = 0.0
    tokens: int = 0
    runtime_seconds: float = 0.0


class CostController:
    """Hard resource guard preventing an autonomous run from exceeding budget."""

    def __init__(self, budget: ResourceBudget) -> None:
        if budget.max_cost < 0:
            raise ValueError("max_cost cannot be negative")
        self.budget = budget
        self.usage = ResourceUsage()

    def record(self, usage: ResourceUsage) -> ResourceUsage:
        candidate = ResourceUsage(
            cost=self.usage.cost + usage.cost,
            tokens=self.usage.tokens + usage.tokens,
            runtime_seconds=self.usage.runtime_seconds + usage.runtime_seconds,
        )
        self._validate(candidate)
        self.usage = candidate
        return self.usage

    def remaining(self) -> ResourceUsage:
        return ResourceUsage(
            cost=max(0.0, self.budget.max_cost - self.usage.cost),
            tokens=(
                max(0, self.budget.max_tokens - self.usage.tokens)
                if self.budget.max_tokens is not None
                else 0
            ),
            runtime_seconds=(
                max(0.0, self.budget.max_runtime_seconds - self.usage.runtime_seconds)
                if self.budget.max_runtime_seconds is not None
                else 0.0
            ),
        )

    def _validate(self, usage: ResourceUsage) -> None:
        if usage.cost > self.budget.max_cost:
            raise RuntimeError("Cost budget exceeded")
        if self.budget.max_tokens is not None and usage.tokens > self.budget.max_tokens:
            raise RuntimeError("Token budget exceeded")
        if (
            self.budget.max_runtime_seconds is not None
            and usage.runtime_seconds > self.budget.max_runtime_seconds
        ):
            raise RuntimeError("Runtime budget exceeded")
