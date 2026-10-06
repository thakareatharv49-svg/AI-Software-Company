from src.company.research import (
    AdvancedResearchEngine,
    CompetitiveIntelligence,
    CompetitorProfile,
    ProductDiscovery,
    ResearchEngine,
    ResearchSource,
    RoadmapGenerator,
    StaticResearchProvider,
)


def engine():
    provider = StaticResearchProvider(
        (
            ResearchSource("1", "AI market", "https://example.com", content="market evidence"),
            ResearchSource("2", "AI market alternatives", "https://example.org", content="alternative evidence"),
        )
    )
    return ResearchEngine(provider)


def test_m76_builds_traceable_research_plan():
    advanced = AdvancedResearchEngine(engine())
    plan = advanced.plan("AI coding tools")
    assert len(plan.subqueries) == 4
    reports = advanced.research("AI market")
    assert reports[0].source_count >= 1


def test_m77_compares_competitors_and_finds_gaps():
    intelligence = CompetitiveIntelligence()
    competitors = [
        CompetitorProfile("A", strengths=("fast",), weaknesses=("expensive",)),
        CompetitorProfile("B", strengths=("simple",), weaknesses=("expensive",)),
    ]
    assert intelligence.analyze(competitors)[0].name == "A"
    assert intelligence.gaps(competitors) == ("expensive",)


def test_m78_discovers_products_from_research():
    reports = advanced_reports = AdvancedResearchEngine(engine()).research("AI market")
    products = ProductDiscovery().discover(list(reports), "developers")
    assert products
    assert products[0].target_user == "developers"


def test_m79_generates_prioritized_roadmap():
    reports = AdvancedResearchEngine(engine()).research("AI market")
    products = ProductDiscovery().discover(list(reports), "developers")
    roadmap = RoadmapGenerator().generate(products)
    assert roadmap
    assert roadmap[0].priority >= roadmap[-1].priority
