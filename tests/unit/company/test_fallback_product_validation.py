from __future__ import annotations

import json

import pytest

from src.company.project_generator import GeneratedProject, OllamaProjectGenerator


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("name", "objective"),
    [
        ("To-do app", "Build a to-do list with task management"),
        ("Calculator", "Create a calculator"),
        ("Tic-Tac-Toe", "Build a Tic-Tac-Toe game"),
        ("Expense Tracker", "Create an expense tracker"),
    ],
)
async def test_deterministic_products_use_shared_validation(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    objective: str,
) -> None:
    validated: list[tuple[str, str, GeneratedProject]] = []

    def record_validation(
        product_name: str,
        product_objective: str,
        project: GeneratedProject,
    ) -> None:
        validated.append((product_name, product_objective, project))

    monkeypatch.setattr(
        OllamaProjectGenerator,
        "_validate_mission_output",
        staticmethod(record_validation),
    )

    project = await OllamaProjectGenerator().generate(name, objective)

    assert project.files
    assert len(validated) == 1
    assert validated[0][0:2] == (name, objective)
    assert validated[0][2] is project


def test_browser_fallback_categories_require_a_root_entry_point() -> None:
    project = GeneratedProject(
        files={"app.js": "console.log('missing entry point')"},
        test_command=["python", "-m", "pytest", "-q"],
    )

    with pytest.raises(RuntimeError, match="missing root index.html"):
        OllamaProjectGenerator._validate_mission_output(
            "Calculator",
            "Create a calculator",
            project,
        )




def test_parsed_browser_product_gets_automated_smoke_test() -> None:
    generator = OllamaProjectGenerator()
    project = generator._parse(
        json.dumps(
            {
                "files": {
                    "index.html": "<!doctype html><html><body><h1>Calculator</h1></body></html>",
                    "app.js": "function calculate(a, b) { return a + b; }",
                },
                "test_command": ["python", "-m", "pytest", "-q"],
            }
        )
    )

    assert "tests/test_generated_project.py" in project.files
    smoke_test = project.files["tests/test_generated_project.py"]
    assert "test_browser_entrypoint_and_local_assets_exist" in smoke_test
    assert "root.rglob('*.css')" in smoke_test
    assert "Missing CSS asset" in smoke_test




@pytest.mark.parametrize(
    "module_source",
    [
        "import './missing.js';",
        "export { start } from './missing.js';",
        "export * from './missing.js';",
    ],
)
def test_browser_asset_validation_rejects_missing_module_dependencies(
    module_source: str,
) -> None:
    files = {
        "index.html": '<!doctype html><script type="module" src="./app.js"></script>',
        "app.js": module_source,
    }

    with pytest.raises(RuntimeError, match="references missing local asset"):
        OllamaProjectGenerator._validate_local_browser_assets(files)


def test_browser_asset_validation_accepts_existing_side_effect_import() -> None:
    files = {
        "index.html": '<!doctype html><script type="module" src="./app.js"></script>',
        "app.js": "import './startup.js';",
        "startup.js": "globalThis.started = true;",
    }

    OllamaProjectGenerator._validate_local_browser_assets(files)

def test_deterministic_fallback_rejects_missing_automated_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = GeneratedProject(
        files={
            "index.html": "<!doctype html><html><body><h1>Inventory</h1></body></html>",
            "app.js": "function addItem(items, item) { return [...items, item]; }",
        },
        test_command=["python", "-m", "pytest", "-q"],
    )
    monkeypatch.setattr(
        OllamaProjectGenerator,
        "_validate_mission_output",
        staticmethod(lambda name, objective, candidate: None),
    )

    with pytest.raises(RuntimeError, match="no automated test files"):
        OllamaProjectGenerator._validated_fallback(
            "Inventory",
            "Build an inventory app",
            project,
        )


def test_deterministic_fallback_accepts_behavior_test_module() -> None:
    project = GeneratedProject(
        files={
            "index.html": "<!doctype html><html><body><h1>Inventory</h1></body></html>",
            "app.js": "function addItem(items, item) { return [...items, item]; }",
            "tests/test_inventory.py": (
                "def test_add_item():\n"
                "    items = []\n"
                "    result = [*items, 'keyboard']\n"
                "    assert result == ['keyboard']\n"
            ),
        },
        test_command=["python", "-m", "pytest", "-q"],
    )
    assert OllamaProjectGenerator._validated_fallback(
        "Inventory",
        "Build an inventory app",
        project,
    ) is project


def test_repaired_large_mission_cannot_remove_its_test_module() -> None:
    project = GeneratedProject(
        files={
            "index.html": "<!doctype html><html><body><h1>Inventory</h1></body></html>",
            "app.js": "function addItem(items, item) { return [...items, item]; }",
        },
        test_command=["python", "-m", "pytest", "-q"],
    )

    with pytest.raises(RuntimeError, match="no automated test files"):
        OllamaProjectGenerator._validate_repaired_output(
            "Inventory Management Platform",
            "Build a responsive inventory web application with create, edit, delete, search, reporting, and user roles",
            project,
        )


def test_repaired_small_mission_keeps_existing_validation_scope() -> None:
    project = GeneratedProject(
        files={
            "index.html": "<!doctype html><html><body><h1>Simple landing page</h1></body></html>",
            "app.js": "console.log('ready');",
        },
        test_command=["python", "-m", "pytest", "-q"],
    )

    OllamaProjectGenerator._validate_repaired_output(
        "Simple landing page",
        "Build a simple landing page",
        project,
    )


@pytest.mark.parametrize(
    ("source_path", "source", "dependency_path"),
    [
        ("styles/main.css", '@import "./tokens.css";', "styles/tokens.css"),
        ("styles/main.css", "body { background-image: url(../assets/bg.svg); }", "assets/bg.svg"),
        ("pages/dashboard.html", '<script src="../app.js"></script>', "app.js"),
        ("pages/dashboard.html", '<link rel="stylesheet" href="../styles/main.css">', "styles/main.css"),
    ],
)
def test_browser_asset_validation_resolves_nested_relative_paths(
    source_path: str,
    source: str,
    dependency_path: str,
) -> None:
    files = {
        "index.html": "<!doctype html><html><body></body></html>",
        source_path: source,
        dependency_path: "/* dependency exists */",
    }

    OllamaProjectGenerator._validate_local_browser_assets(files)


@pytest.mark.parametrize(
    ("source_path", "source"),
    [
        ("styles/main.css", '@import "./missing.css";'),
        ("styles/main.css", "body { background-image: url(../assets/missing.svg); }"),
        ("pages/dashboard.html", '<script src="../missing.js"></script>'),
        ("pages/dashboard.html", '<link rel="stylesheet" href="../missing.css">'),
    ],
)
def test_browser_asset_validation_rejects_missing_nested_relative_paths(
    source_path: str,
    source: str,
) -> None:
    files = {
        "index.html": "<!doctype html><html><body></body></html>",
        source_path: source,
    }

    with pytest.raises(RuntimeError, match="references missing local asset"):
        OllamaProjectGenerator._validate_local_browser_assets(files)
