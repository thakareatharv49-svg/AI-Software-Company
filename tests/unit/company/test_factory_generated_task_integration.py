from __future__ import annotations

from types import SimpleNamespace

from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.manager.models.contracts import TaskPlanItem


def _request(files, tasks=()):
    return SimpleNamespace(
        files=files,
        tasks=tasks,
        project_request=SimpleNamespace(
            name="Inventory",
            objective="Build an inventory app with a browser UI and Python services.",
        ),
    )


def test_factory_expands_single_task_for_multi_subsystem_generated_product() -> None:
    request = _request({
        "index.html": "<main>Inventory</main>",
        "src/services/inventory.py": "def list_items(): return []",
        "src/models/item.py": "class Item: pass",
        "tests/test_inventory.py": "def test_list_items(): assert [] == []",
    }, tasks=(TaskPlanItem(title="Build inventory", description="Build the app"),))

    tasks = FactoryAutonomousRunner._derive_tasks_from_generated_files(
        request, SimpleNamespace(objective=request.project_request.objective)
    )

    assert len(tasks) == 4
    assert any("src/services" in task.title for task in tasks)
    assert any("src/models" in task.title for task in tasks)
    assert tasks[-1].dependencies == (0, 1, 2)


def test_factory_preserves_explicit_multi_task_plan() -> None:
    explicit = (
        TaskPlanItem(title="Backend", dependencies=()),
        TaskPlanItem(title="Frontend", dependencies=(0,)),
    )
    request = _request({"index.html": "<main>Inventory</main>"}, tasks=explicit)

    assert FactoryAutonomousRunner._derive_tasks_from_generated_files(
        request, SimpleNamespace(objective=request.project_request.objective)
    ) is explicit
