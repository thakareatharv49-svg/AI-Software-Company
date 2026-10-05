from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class UsageRecord:
    actor: str
    project_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    model_cost: Decimal = Decimal("0")
    infrastructure_cost: Decimal = Decimal("0")

    @property
    def total_cost(self) -> Decimal:
        return self.model_cost + self.infrastructure_cost

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class Budget:
    project_id: str
    limit: Decimal


@dataclass(frozen=True)
class CostSummary:
    project_id: str
    tokens: int
    cost: Decimal
    budget: Decimal | None
    remaining: Decimal | None
    within_budget: bool


class CostController:
    """M38 bounded cost accounting and spending control."""

    def __init__(self) -> None:
        self._usage: list[UsageRecord] = []
        self._budgets: dict[str, Budget] = {}

    def set_budget(self, project_id: str, limit: Decimal) -> Budget:
        if limit < 0:
            raise ValueError("budget cannot be negative")
        budget = Budget(project_id, limit)
        self._budgets[project_id] = budget
        return budget

    def record(self, usage: UsageRecord) -> CostSummary:
        if usage.input_tokens < 0 or usage.output_tokens < 0:
            raise ValueError("token usage cannot be negative")
        if usage.total_cost < 0:
            raise ValueError("cost cannot be negative")
        self._usage.append(usage)
        return self.summary(usage.project_id)

    def summary(self, project_id: str) -> CostSummary:
        records = [item for item in self._usage if item.project_id == project_id]
        cost = sum((item.total_cost for item in records), Decimal("0"))
        tokens = sum(item.total_tokens for item in records)
        budget = self._budgets.get(project_id)
        remaining = budget.limit - cost if budget else None
        return CostSummary(
            project_id=project_id,
            tokens=tokens,
            cost=cost,
            budget=budget.limit if budget else None,
            remaining=remaining,
            within_budget=budget is None or cost <= budget.limit,
        )

    def authorize(self, project_id: str, estimated_cost: Decimal) -> bool:
        if estimated_cost < 0:
            raise ValueError("estimated cost cannot be negative")
        summary = self.summary(project_id)
        return summary.budget is None or summary.cost + estimated_cost <= summary.budget
