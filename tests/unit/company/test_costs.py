from decimal import Decimal

import pytest

from company.costs import CostController, UsageRecord


def test_cost_controller_tracks_budget_and_tokens() -> None:
    controller = CostController()
    controller.set_budget("p1", Decimal("2.00"))
    summary = controller.record(
        UsageRecord("agent", "p1", input_tokens=100, output_tokens=50, model_cost=Decimal("1.25"))
    )
    assert summary.tokens == 150
    assert summary.cost == Decimal("1.25")
    assert summary.remaining == Decimal("0.75")
    assert summary.within_budget
    assert controller.authorize("p1", Decimal("0.75"))
    assert not controller.authorize("p1", Decimal("0.76"))


def test_cost_controller_rejects_negative_values() -> None:
    with pytest.raises(ValueError):
        UsageRecord("agent", "p1", input_tokens=-1)
