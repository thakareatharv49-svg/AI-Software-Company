from company.autonomy import (
    CompanyAutonomy,
    LearningService,
    ProductPortfolioService,
    ResourceAllocator,
    ProjectCandidate,
    ProjectSelector,
)

def test_m96_multi_product_portfolio():
    portfolio = ProductPortfolioService().build(["a", "b"], "a")
    assert portfolio.products == ("a", "b")

def test_m97_resource_allocation():
    assert ResourceAllocator().allocate("a", 10, 2).budget == 10

def test_m98_project_selection():
    selected = ProjectSelector().select(
        [ProjectCandidate("a", 8, 1), ProjectCandidate("b", 5, 0)]
    )
    assert selected.name == "a"

def test_m99_company_learning():
    assert LearningService().learn(["signal"], ["lesson"], 0.9).confidence == 0.9

def test_m100_autonomous_company_cycle():
    portfolio = ProductPortfolioService().build(["a"], "a")
    allocation = ResourceAllocator().allocate("a", 10, 2)
    learning = LearningService().learn(["signal"], ["lesson"], 1.0)
    cycle = CompanyAutonomy().run_cycle(
        portfolio, [ProjectCandidate("a", 8)], allocation, learning
    )
    assert cycle.selected_project == "a"
    assert cycle.status == "planned"
