from src.company.intelligence import (
    CostController,
    CrossProjectMemory,
    DecisionEngine,
    DecisionOption,
    LearningEngine,
    LearningSignal,
    MemoryInsight,
    PortfolioManager,
    ResourceBudget,
    ResourceUsage,
)


def test_cross_project_memory_searches_reusable_insights():
    memory = CrossProjectMemory()
    memory.remember(MemoryInsight("testing", "pytest reduced failures", "p1"))
    memory.remember(MemoryInsight("testing", "pytest improved confidence", "p2"))

    results = memory.search("pytest")

    assert len(results) == 2
    assert {item.project_id for item in results} == {"p1", "p2"}


def test_learning_engine_tracks_success_and_lessons():
    learning = LearningEngine()
    learning.record(LearningSignal("qa", "pass", 1.0))
    learning.record(LearningSignal("qa", "pass", 1.0))
    learning.record(LearningSignal("qa", "fail", -1.0))

    assert learning.success_rate("qa") == 2 / 3
    assert "pass" in learning.lessons("qa")[0]


def test_decision_engine_accounts_for_risk_and_cost():
    engine = DecisionEngine()
    result = engine.choose([
        DecisionOption("cheap", 7, risk=1, cost=1, confidence=1),
        DecisionOption("valuable", 10, risk=2, cost=1, confidence=1),
    ])

    assert result.selected.name == "valuable"


def test_cost_controller_enforces_budget():
    controller = CostController(ResourceBudget(max_cost=5, max_tokens=100))
    controller.record(ResourceUsage(cost=2, tokens=50))

    assert controller.remaining().cost == 3

    try:
        controller.record(ResourceUsage(cost=4))
    except RuntimeError as exc:
        assert str(exc) == "Cost budget exceeded"
    else:
        raise AssertionError("budget should have blocked")


def test_portfolio_manager_ranks_and_selects_projects():
    portfolio = PortfolioManager()
    projects = [
        portfolio.score(project_id="1", name="A", expected_value=10, risk=1, cost=1, confidence=1),
        portfolio.score(project_id="2", name="B", expected_value=20, risk=1, cost=2, confidence=1),
    ]

    assert portfolio.rank(projects)[0].name == "B"
    assert [p.name for p in portfolio.select(projects, 1)] == ["B"]
