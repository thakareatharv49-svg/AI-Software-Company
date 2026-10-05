from decimal import Decimal

from company.economics import CompanyEconomics, Opportunity


def opportunity(
    identifier: str,
    value: str,
    cost: str,
    strategic_fit: str,
    risk: str,
) -> Opportunity:
    return Opportunity(
        identifier,
        identifier,
        Decimal(value),
        Decimal(cost),
        Decimal(strategic_fit),
        Decimal(risk),
    )


def test_prioritize_with_budget() -> None:
    result = CompanyEconomics().prioritize(
        [
            opportunity("a", "10", "3", "4", "1"),
            opportunity("b", "8", "2", "1", "1"),
            opportunity("c", "1", "1", "0", "2"),
        ],
        Decimal("5"),
    )
    assert result.selected == ("a", "b")
    assert result.total_cost == Decimal("5")
