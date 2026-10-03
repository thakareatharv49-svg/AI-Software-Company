from src.agents.engineering import (
    EngineeringAgentCatalog,
    EngineeringAgentSpec,
    EngineeringRole,
    create_default_engineering_catalog,
)


def test_default_engineering_agents():
    catalog = create_default_engineering_catalog()

    agents = catalog.list_agents()

    expected = {
        "frontend-engineer",
        "backend-engineer",
        "ai-engineer",
        "database-engineer",
        "infrastructure-engineer",
    }

    assert len(agents) == 5
    assert {agent.name for agent in agents} == expected


def test_find_agents_by_role():
    catalog = create_default_engineering_catalog()

    agents = catalog.by_role(EngineeringRole.BACKEND)

    assert len(agents) == 1
    assert agents[0].name == "backend-engineer"


def test_register_custom_engineering_agent():
    catalog = EngineeringAgentCatalog()

    catalog.register(
        EngineeringAgentSpec(
            name="custom-backend",
            role=EngineeringRole.BACKEND,
            capabilities=["python"],
        )
    )

    assert catalog.get("custom-backend").role == EngineeringRole.BACKEND


def test_duplicate_engineering_agent_rejected():
    catalog = create_default_engineering_catalog()

    try:
        catalog.register(
            EngineeringAgentSpec(
                name="frontend-engineer",
                role=EngineeringRole.FRONTEND,
            )
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected duplicate registration to fail")
