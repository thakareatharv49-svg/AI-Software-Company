from __future__ import annotations

from company.research.engine import (
    ResearchEngine,
    ResearchFinding,
    ResearchReport,
    ResearchSource,
    StaticResearchProvider,
)

__all__ = [
    "ResearchEngine",
    "ResearchFinding",
    "ResearchReport",
    "ResearchSource",
    "StaticResearchProvider",
]

from src.company.research.advanced import AdvancedResearchEngine, ResearchPlan
from src.company.research.market import CompetitorProfile, CompetitiveIntelligence, MarketSignal
from src.company.research.product_discovery import ProductCandidate, ProductDiscovery
from src.company.research.roadmap import RoadmapGenerator, RoadmapItem
