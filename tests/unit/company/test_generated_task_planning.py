from __future__ import annotations

import pytest

from src.company.generated_task_planning import build_generated_task_plan


def test_generated_files_become_parallel_ready_subsystem_work_packages() -> None:
    tasks = build_generated_task_plan(
        "Inventory",
        "Build an inventory application with item management.",
        {
            "index.html": "<main></main>",
            "src/services/inventory.py": "class Inventory: pass",
            "src/models/item.py": "class Item: pass",
            "tests/test_inventory.py": "def test_inventory(): pass",
        },
    )

    assert len(tasks) == 4
    assert [task.title for task in tasks] == [
        "Integrate Inventory: application shell",
        "Integrate Inventory: src/services",
        "Integrate Inventory: src/models",
        "Validate Inventory quality and tests",
    ]
    # Implementation packages are independent; schedulers may execute them concurrently.
    assert tasks[0].dependencies == ()
    assert tasks[1].dependencies == ()
    assert tasks[2].dependencies == ()
    # QA cannot start until every implementation package is complete.
    assert tasks[3].dependencies == (0, 1, 2)
    assert "src/services/inventory.py" in tasks[1].description
    assert "tests/test_inventory.py" in tasks[3].description


def test_task_planning_groups_root_browser_assets_as_one_shell() -> None:
    tasks = build_generated_task_plan(
        "Notes",
        "Build a notes app.",
        {"index.html": "", "style.css": "", "app.js": ""},
    )

    assert len(tasks) == 1
    assert "application shell" in tasks[0].title
    assert tasks[0].dependencies == ()


def test_task_planning_rejects_empty_or_unsafe_file_maps() -> None:
    with pytest.raises(ValueError, match="no generated files"):
        build_generated_task_plan("Empty", "Objective", {})
    with pytest.raises(ValueError, match="Unsafe generated file path"):
        build_generated_task_plan("Unsafe", "Objective", {"../escape.py": ""})
