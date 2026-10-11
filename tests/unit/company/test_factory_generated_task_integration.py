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

def test_factory_keeps_single_task_for_single_subsystem_browser_product() -> None:
    broad_task = TaskPlanItem(title="Build Notes", description="Build the notes app")
    request = _request(
        {
            "index.html": "<main>Notes</main>",
            "style.css": "main { color: black; }",
            "app.js": "const notes = [];",
        },
        tasks=(broad_task,),
    )

    tasks = FactoryAutonomousRunner._derive_tasks_from_generated_files(
        request, SimpleNamespace(objective=request.project_request.objective)
    )

    # Root browser assets form one coherent subsystem; avoid needless task fan-out.
    assert tasks == (broad_task,)


def test_factory_derives_work_packages_when_browser_and_backend_are_generated() -> None:
    request = _request(
        {
            "index.html": "<main>Inventory</main>",
            "app.js": "const inventory = [];",
            "src/api/items.py": "def list_items(): return []",
            "src/models/item.py": "class Item: pass",
            "tests/test_items.py": (
                "def test_item_count():\\n"
                "    items = [1, 2]\\n"
                "    assert len(items) == 2\\n"
            ),
        },
        tasks=(TaskPlanItem(title="Build Inventory", description="Build everything"),),
    )

    tasks = FactoryAutonomousRunner._derive_tasks_from_generated_files(
        request, SimpleNamespace(objective=request.project_request.objective)
    )

    implementation = [task for task in tasks if not task.title.startswith("Validate ")]
    quality = [task for task in tasks if task.title.startswith("Validate ")]

    assert len(implementation) >= 2
    assert len(quality) == 1
    assert quality[0].dependencies == tuple(range(len(implementation)))

