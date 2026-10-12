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
        "Integrate Inventory: frontend",
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


def test_task_planning_groups_root_browser_assets_as_frontend_work() -> None:
    tasks = build_generated_task_plan(
        "Notes",
        "Build a notes app.",
        {
            "index.html": "<main>Notes</main>",
            "style.css": "main { display: block; }",
            "app.js": "const notes = [];",
        },
    )

    assert len(tasks) == 1
    assert tasks[0].title == "Integrate Notes: frontend"
    assert tasks[0].dependencies == ()


def test_task_planning_rejects_empty_or_unsafe_file_maps() -> None:
    with pytest.raises(ValueError, match="no generated files"):
        build_generated_task_plan("Empty", "Objective", {})
    with pytest.raises(ValueError, match="Unsafe generated file path"):
        build_generated_task_plan("Unsafe", "Objective", {"../escape.py": ""})



def test_task_planning_rejects_parent_traversal_in_nested_paths() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unsafe generated file path"):
        build_generated_task_plan(
            "Unsafe",
            "Objective",
            {"src/../../outside.py": "print('unsafe')"},
        )


def test_task_planning_rejects_duplicate_paths_after_separator_normalization() -> None:
    import pytest

    with pytest.raises(ValueError, match="Duplicate generated file path"):
        build_generated_task_plan(
            "Duplicate",
            "Objective",
            {"src/app.py": "print('first')", r"src\app.py": "print('second')"},
        )


def test_task_planning_rejects_all_empty_generated_files() -> None:
    with pytest.raises(ValueError, match="entirely empty"):
        build_generated_task_plan(
            "Empty output",
            "Build a working application",
            {"index.html": "  \n", "app.js": ""},
        )


def test_task_planning_requires_implementation_not_only_tests() -> None:
    with pytest.raises(ValueError, match="without generated implementation files"):
        build_generated_task_plan(
            "Test-only output",
            "Build a working application",
            {"tests/test_app.py": "def test_app():\n    assert True\n"},
        )

def test_root_level_backend_modules_get_a_separate_integration_package() -> None:
    tasks = build_generated_task_plan(
        "Inventory",
        "Build an inventory browser app backed by a Python API.",
        {
            "index.html": "<main>Inventory</main>",
            "app.js": "const items = [];",
            "server.py": "def list_items(): return []",
            "models.py": "class Item: pass",
            "tests/test_inventory.py": (
                "def test_item_count():\\n"
                "    items = [1, 2]\\n"
                "    assert len(items) == 2\\n"
            ),
        },
    )

    titles = [task.title for task in tasks]
    assert "Integrate Inventory: frontend" in titles
    assert "Integrate Inventory: backend" in titles
    qa_task = tasks[-1]
    assert qa_task.title == "Validate Inventory quality and tests"
    assert qa_task.dependencies == tuple(range(len(tasks) - 1))

