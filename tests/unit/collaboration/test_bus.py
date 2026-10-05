from company.collaboration.bus import CollaborationBus, CollaborationMessage, Handoff
from company.collaboration.coordination import AgentDependency, DependencyCoordinator


def test_collaboration_bus_routes_messages_and_handoffs() -> None:
    bus = CollaborationBus()
    bus.send(CollaborationMessage("researcher", "engineer", "Use Python."))
    bus.handoff(Handoff("task-1", "researcher", "engineer", {"finding": "Python"}))

    synced = bus.synchronize("engineer")

    assert len(synced["messages"]) == 1
    assert len(synced["handoffs"]) == 1
    assert synced["handoffs"][0].task_id == "task-1"


def test_dependency_coordinator_blocks_until_dependencies_complete() -> None:
    coordinator = DependencyCoordinator(
        (AgentDependency("build", ("research", "design")),)
    )

    assert coordinator.ready("build") is False
    coordinator.mark_complete("research")
    assert coordinator.ready("build") is False
    coordinator.mark_complete("design")
    assert coordinator.ready("build") is True


def test_independent_task_is_ready() -> None:
    assert DependencyCoordinator().ready("independent") is True
