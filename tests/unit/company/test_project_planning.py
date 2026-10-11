import asyncio
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
