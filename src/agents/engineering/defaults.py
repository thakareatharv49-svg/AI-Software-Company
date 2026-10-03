from src.agents.engineering.catalog import EngineeringAgentCatalog
from src.agents.engineering.enums import EngineeringRole

DEFAULT_ENGINEERING_AGENTS = (
    ("frontend-engineer", EngineeringRole.FRONTEND, [
        "react",
        "typescript",
        "ui",
        "frontend",
    ]),
    ("backend-engineer", EngineeringRole.BACKEND, [
        "python",
        "fastapi",
        "api",
        "backend",
    ]),
    ("ai-engineer", EngineeringRole.AI, [
        "llm",
        "prompting",
        "agents",
        "ai",
    ]),
    ("database-engineer", EngineeringRole.DATABASE, [
        "postgresql",
        "sql",
        "schema",
        "database",
    ]),
    ("infrastructure-engineer", EngineeringRole.INFRASTRUCTURE, [
        "docker",
        "ci",
        "deployment",
        "infrastructure",
    ]),
)


def create_default_engineering_catalog() -> EngineeringAgentCatalog:
    catalog = EngineeringAgentCatalog()

    for name, role, capabilities in DEFAULT_ENGINEERING_AGENTS:
        catalog.register(
            __import__(
                "src.agents.engineering.catalog",
                fromlist=["EngineeringAgentSpec"],
            ).EngineeringAgentSpec(
                name=name,
                role=role,
                capabilities=capabilities,
            )
        )

    return catalog
