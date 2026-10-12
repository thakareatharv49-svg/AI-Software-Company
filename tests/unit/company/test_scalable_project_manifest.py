from __future__ import annotations

import asyncio
import json

from src.company.project_generator import MAX_GENERATED_PROJECT_FILES, OllamaProjectGenerator


def test_large_mission_supports_modular_projects_above_ten_files(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    file_count = 12
    manifest = [
        {
            "path": "tests/test_project.py" if index == file_count - 1 else f"src/modules/module_{index:02}.py",
            "purpose": "Behavioral tests" if index == file_count - 1 else f"Inventory module {index}",
        }
        for index in range(file_count)
    ]
    calls = 0

    async def fake_call(payload: dict) -> str:
        nonlocal calls
        calls += 1
        prompt = payload["prompt"]
        if calls == 1:
            assert f"{MAX_GENERATED_PROJECT_FILES} files" in prompt
            return json.dumps({"files": manifest})
        path = prompt.split("File to generate: ", 1)[1].splitlines()[0]
        if path == "tests/test_project.py":
            source = (
                "def test_inventory_total_includes_all_items():\n"
                "    quantities = [2, 3, 5]\n"
                "    assert sum(quantities) == 10\n"
            )
        else:
            source = "def inventory_value(quantity, unit_price):\n    return quantity * unit_price\n"
        return json.dumps({"content": source})

    generator._call = fake_call  # type: ignore[method-assign]
    project = asyncio.run(
        generator._generate_large_mission(
            "Command-line Inventory Platform",
            "Build a command-line inventory management platform with search, create, "
            "edit, delete, export, and reporting workflows.",
        )
    )

    assert len(project.files) == file_count
    assert len(project.files) > 10
    assert "src/modules/module_00.py" in project.files
    assert "src/modules/module_10.py" in project.files
    assert "tests/test_project.py" in project.files
    assert calls == file_count + 1


def test_generated_project_file_budget_is_bounded_but_not_ten_files() -> None:
    assert MAX_GENERATED_PROJECT_FILES == 40
    assert MAX_GENERATED_PROJECT_FILES > 10


def test_compact_manifest_retry_uses_configured_file_budget(tmp_path) -> None:
    generator = OllamaProjectGenerator(
        checkpoint_dir=tmp_path,
        max_generated_project_files=8,
    )
    oversized = [
        {
            "path": "tests/test_project.py" if index == 8 else f"src/modules/module_{index:02}.py",
            "purpose": "Behavioral tests" if index == 8 else f"Inventory module {index}",
        }
        for index in range(9)
    ]
    compact = [
        {"path": "src/inventory.py", "purpose": "Inventory behavior"},
        {"path": "src/reports.py", "purpose": "Inventory reporting"},
        {"path": "src/cli.py", "purpose": "Command-line interface"},
        {"path": "tests/test_project.py", "purpose": "Behavioral tests"},
    ]
    calls = 0

    async def fake_call(payload: dict) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            assert "no more than 8 files for this generation run" in payload["prompt"]
            return json.dumps({"files": oversized})
        if calls == 2:
            assert "no more than 8 files total" in payload["prompt"]
            return json.dumps({"files": compact})
        path = payload["prompt"].split("File to generate: ", 1)[1].splitlines()[0]
        source = (
            "def test_inventory_total_includes_all_items():\n"
            "    quantities = [2, 3, 5]\n"
            "    assert sum(quantities) == 10\n"
            if path == "tests/test_project.py"
            else "def inventory_value(quantity, unit_price):\n    return quantity * unit_price\n"
        )
        return json.dumps({"content": source})

    generator._call = fake_call  # type: ignore[method-assign]
    project = asyncio.run(
        generator._generate_large_mission(
            "Command-line Inventory Platform",
            "Build a command-line inventory management platform with search, create, "
            "edit, delete, export, and reporting workflows.",
        )
    )

    assert set(project.files) == {item["path"] for item in compact}
    assert len(project.files) <= 8
    assert calls == len(compact) + 2

