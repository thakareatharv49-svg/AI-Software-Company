import json

import pytest

from src.company.project_generator import OllamaProjectGenerator
from src.company.project_planning import order_manifest_paths


def test_manifest_orders_dependencies_before_consumers_stably() -> None:
    paths = ["tests/test_service.py", "src/service.py", "src/contracts.py"]
    dependencies = {
        "tests/test_service.py": ["src/service.py"],
        "src/service.py": ["src/contracts.py"],
        "src/contracts.py": [],
    }

    assert order_manifest_paths(paths, dependencies) == [
        "src/contracts.py",
        "src/service.py",
        "tests/test_service.py",
    ]


@pytest.mark.parametrize(
    ("paths", "dependencies", "message"),
    [
        (["a.py"], {"a.py": ["a.py"]}, "cannot depend on itself"),
        (["a.py"], {"a.py": ["missing.py"]}, "unknown path"),
        (["a.py", "b.py"], {"a.py": ["b.py"], "b.py": ["a.py"]}, "dependency cycle"),
        (["a.py", "a.py"], {}, "duplicate paths"),
        (["a.py"], {"a.py": ["b.py", "b.py"]}, "repeats a dependency"),
    ],
)
def test_manifest_rejects_invalid_dependency_graphs(paths, dependencies, message) -> None:
    with pytest.raises(ValueError, match=message):
        order_manifest_paths(paths, dependencies)


@pytest.mark.asyncio
async def test_large_mission_generates_modules_in_dependency_order(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    manifest = {
        "files": [
            {"path": "tests/test_service.py", "purpose": "Behavioral service tests", "depends_on": ["src/service.py"]},
            {"path": "src/service.py", "purpose": "Inventory service", "depends_on": ["src/contracts.py"]},
            {"path": "src/contracts.py", "purpose": "Inventory data contracts", "depends_on": []},
        ]
    }
    responses = [
        json.dumps(manifest),
        json.dumps({"content": "class InventoryItem:\n    def __init__(self, name):\n        self.name = name\n"}),
        json.dumps({"content": "from src.contracts import InventoryItem\n\ndef create_item(name):\n    return InventoryItem(name)\n"}),
        json.dumps({"content": "from src.service import create_item\n\ndef test_create_item_preserves_name():\n    assert create_item('Notebook').name == 'Notebook'\n"}),
    ]
    generated_order = []

    async def fake_call(payload):
        if "File to generate: " in payload["prompt"]:
            generated_order.append(
                payload["prompt"].split("File to generate: ", 1)[1].splitlines()[0]
            )
        return responses.pop(0)

    generator._call = fake_call  # type: ignore[method-assign]
    project = await generator._generate_large_mission(
        "Inventory CLI",
        "Build a Python command-line inventory tool with item creation and validation.",
    )

    assert generated_order == [
        "src/contracts.py",
        "src/service.py",
        "tests/test_service.py",
    ]
    assert set(project.files) == set(generated_order)



@pytest.mark.asyncio
async def test_large_manifest_enforces_file_limit_and_recovers(tmp_path) -> None:
    generator = OllamaProjectGenerator(
        checkpoint_dir=tmp_path,
        max_generated_project_files=4,
    )
    oversized = {
        "files": [
            {"path": f"src/module_{index}.py", "purpose": "Module", "depends_on": []}
            for index in range(5)
        ]
    }
    valid = {
        "files": [
            {"path": "src/contracts.py", "purpose": "Contracts", "depends_on": []},
            {"path": "src/service.py", "purpose": "Service", "depends_on": ["src/contracts.py"]},
            {"path": "tests/test_service.py", "purpose": "Behavior tests", "depends_on": ["src/service.py"]},
            {"path": "README.md", "purpose": "Usage", "depends_on": []},
        ]
    }
    responses = [
        json.dumps(oversized),
        json.dumps(valid),
        json.dumps({"content": "class Contract: pass"}),
        json.dumps({"content": "from src.contracts import Contract\ndef create(): return Contract()"}),
        json.dumps({"content": "from src.service import create\ndef test_create(): assert create() is not None"}),
        json.dumps({"content": "# Inventory"}),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    generator._call = fake_call  # type: ignore[method-assign]
    generated = await generator._generate_large_mission(
        "Inventory CLI",
        "Build an inventory CLI with create, edit, search, filter, export and validation.",
    )

    assert len(generated.files) == 4
    assert "exceeded the safe 4-file limit" in prompts[1]


@pytest.mark.asyncio
async def test_large_manifest_normalizes_windows_paths_and_rejects_case_duplicates(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path, max_generated_project_files=4)
    invalid = {
        "files": [
            {"path": "src\\service.py", "purpose": "Service", "depends_on": []},
            {"path": "SRC/service.py", "purpose": "Duplicate on Windows", "depends_on": []},
        ]
    }
    valid = {
        "files": [
            {"path": "src\\contracts.py", "purpose": "Contracts", "depends_on": []},
            {"path": "src\\service.py", "purpose": "Service", "depends_on": ["src\\contracts.py"]},
            {"path": "tests\\test_service.py", "purpose": "Tests", "depends_on": ["src\\service.py"]},
            {"path": "README.md", "purpose": "Readme", "depends_on": []},
        ]
    }
    responses = [
        json.dumps(invalid),
        json.dumps(valid),
        json.dumps({"content": "class Contract: pass"}),
        json.dumps({"content": "from src.contracts import Contract\ndef create(): return Contract()"}),
        json.dumps({"content": "from src.service import create\ndef test_create(): assert create() is not None"}),
        json.dumps({"content": "# Inventory"}),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    generator._call = fake_call  # type: ignore[method-assign]
    generated = await generator._generate_large_mission(
        "Inventory CLI",
        "Build an inventory CLI with create, edit, search, filter, export and validation.",
    )

    assert set(generated.files) == {
        "src/contracts.py", "src/service.py", "tests/test_service.py", "README.md"
    }
    assert "case-insensitive" in prompts[1]
