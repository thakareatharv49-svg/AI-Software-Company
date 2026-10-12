from __future__ import annotations

import asyncio
import json

from src.company.project_generator import OllamaProjectGenerator


def test_non_demo_mission_uses_mission_specific_preview_ready_prompt() -> None:
    generator = OllamaProjectGenerator()
    captured: dict = {}

    async def fake_call(payload: dict) -> str:
        captured.update(payload)
        return json.dumps(
            {
                "files": {
                    "index.html": "<!doctype html><html><head><title>Expense Tracker</title></head><body><h1>Expense Tracker</h1><script src='app.js'></script></body></html>",
                    "app.js": "document.querySelector('h1').textContent = 'Expense Tracker';",
                    "style.css": "body { font-family: sans-serif; }",
                    "tests/test_app.py": (
                        "def test_expense_totals_include_each_expense():\n"
                        "    expenses = [{\"amount\": 12}, {\"amount\": 8}]\n"
                        "    total = sum(item[\"amount\"] for item in expenses)\n"
                        "    assert total == 20\n"
                    ),
                },
                "test_command": ["python", "-m", "pytest", "-q"],
            }
        )

    generator._call = fake_call  # type: ignore[method-assign]
    project = asyncio.run(
        generator.generate(
            "Personal Expense Tracker",
            "Build a personal expense tracker with categories, monthly budgets, and spending summaries.",
        )
    )

    prompt = captured["prompt"].lower()
    assert "personal expense tracker" in prompt
    assert "do not default to a calculator, tic-tac-toe" in prompt
    assert "domain-specific workflows" in prompt
    assert "browser-based application" in prompt
    assert "index.html" in project.files
    assert "app.js" in project.files
    assert "tests/test_app.py" in project.files
    assert captured["options"]["num_predict"] == 8192


def test_calculator_fallback_is_only_selected_for_calculator_missions() -> None:
    generator = OllamaProjectGenerator()
    called = False

    async def unexpected_call(payload: dict) -> str:
        nonlocal called
        called = True
        raise AssertionError("Known calculator fallback should not call Ollama")

    generator._call = unexpected_call  # type: ignore[method-assign]
    project = asyncio.run(
        generator.generate("Calculator", "Build a calculator with basic arithmetic")
    )

    assert not called
    assert "index.html" in project.files



def test_browser_product_missing_entry_point_is_rejected() -> None:
    from src.company.project_generator import GeneratedProject

    try:
        OllamaProjectGenerator._validate_mission_output(
            "Expense Tracker",
            "Build a web app for tracking monthly expenses.",
            GeneratedProject(
                files={"app.js": "console.log('expenses')"},
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
    except RuntimeError as exc:
        assert "index.html" in str(exc)
    else:
        raise AssertionError("A browser product without index.html must be rejected")


def test_browser_product_missing_local_asset_is_rejected() -> None:
    from src.company.project_generator import GeneratedProject

    try:
        OllamaProjectGenerator._validate_mission_output(
            "Study Planner",
            "Build a browser app for planning study sessions.",
            GeneratedProject(
                files={
                    "index.html": '<html><head><script src="app.js"></script></head></html>',
                },
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
    except RuntimeError as exc:
        assert "app.js" in str(exc)
    else:
        raise AssertionError("A browser product with a missing local asset must be rejected")


def test_browser_product_with_local_assets_passes_validation() -> None:
    from src.company.project_generator import GeneratedProject

    OllamaProjectGenerator._validate_mission_output(
        "Study Planner",
        "Build a browser app for planning study sessions.",
        GeneratedProject(
            files={
                "index.html": '<html><head><link rel="stylesheet" href="style.css"><script src="app.js"></script></head></html>',
                "style.css": "body { font-family: sans-serif; }",
                "app.js": "document.title = 'Study Planner';",
            },
            test_command=["python", "-m", "pytest", "-q"],
        ),
    )



def test_browser_validation_failure_triggers_one_mission_aware_repair() -> None:
    from src.company.project_generator import GeneratedProject

    generator = OllamaProjectGenerator()
    repair_calls: list[tuple[dict[str, str], str]] = []

    async def fake_call(payload: dict) -> str:
        return json.dumps({
            "files": {"app.js": "console.log('expenses')"},
            "test_command": ["python", "-m", "pytest", "-q"],
        })

    async def fake_repair(files: dict[str, str], failure: str) -> GeneratedProject:
        repair_calls.append((files, failure))
        return GeneratedProject(
            files={
                "index.html": '<html><head><script src="app.js"></script></head><body><h1>Expense Tracker</h1></body></html>',
                "app.js": "document.title = 'Expense Tracker';",
            },
            test_command=["python", "-m", "pytest", "-q"],
        )

    generator._call = fake_call  # type: ignore[method-assign]
    generator.repair = fake_repair  # type: ignore[method-assign]

    project = asyncio.run(
        generator.generate(
            "Personal Expense Tracker",
            "Build a browser app with monthly budgets and category summaries.",
        )
    )

    assert len(repair_calls) == 1
    assert "Personal Expense Tracker" in repair_calls[0][1]
    assert "monthly budgets and category summaries" in repair_calls[0][1]
    assert "index.html" in project.files
    assert "app.js" in project.files


def test_browser_product_still_fails_if_repair_output_is_invalid() -> None:
    from src.company.project_generator import GeneratedProject

    generator = OllamaProjectGenerator()

    async def fake_call(payload: dict) -> str:
        return json.dumps({
            "files": {"app.js": "console.log('study')"},
            "test_command": ["python", "-m", "pytest", "-q"],
        })

    async def fake_repair(files: dict[str, str], failure: str) -> GeneratedProject:
        return GeneratedProject(
            files={"index.html": '<html><script src="missing.js"></script></html>'},
            test_command=["python", "-m", "pytest", "-q"],
        )

    generator._call = fake_call  # type: ignore[method-assign]
    generator.repair = fake_repair  # type: ignore[method-assign]

    try:
        asyncio.run(
            generator.generate(
                "Study Planner",
                "Build a browser app for planning study sessions.",
            )
        )
    except RuntimeError as exc:
        assert "after one repair" in str(exc)
        assert "missing.js" in str(exc)
    else:
        raise AssertionError("Invalid output after repair must still fail validation")



def test_browser_product_accepts_dot_relative_local_assets() -> None:
    from src.company.project_generator import GeneratedProject

    OllamaProjectGenerator._validate_mission_output(
        "Study Planner",
        "Build a browser app for planning study sessions.",
        GeneratedProject(
            files={
                "index.html": '<html><head><link rel="stylesheet" href="./style.css"><script src="./app.js"></script></head></html>',
                "style.css": "body { font-family: sans-serif; }",
                "app.js": "document.title = 'Study Planner';",
            },
            test_command=["python", "-m", "pytest", "-q"],
        ),
    )

def test_browser_only_project_gets_browser_smoke_test_instead_of_python_requirement(tmp_path) -> None:
    generator = OllamaProjectGenerator()
    project = generator._parse(json.dumps({
        "files": {
            "index.html": "<!doctype html><html><head><link rel='stylesheet' href='./style.css'></head><body><h1>Expense Tracker</h1><script src='./app.js'></script></body></html>",
            "style.css": "body { font-family: sans-serif; }",
            "app.js": "document.querySelector('h1').textContent = 'Expense Tracker';",
        },
        "test_command": ["python", "-m", "pytest", "-q"],
    }))

    generated_test = project.files["tests/test_generated_project.py"]
    assert "test_browser_entrypoint_and_local_assets_exist" in generated_test
    assert "Generated Python source files are missing" not in generated_test

    for relative_path, content in project.files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    test_path = tmp_path / "tests/test_generated_project.py"
    namespace = {"__file__": str(test_path)}
    exec(compile(generated_test, str(test_path), "exec"), namespace)
    namespace["test_browser_entrypoint_and_local_assets_exist"]()


def test_browser_smoke_test_fails_when_a_referenced_local_asset_is_missing(tmp_path) -> None:
    generator = OllamaProjectGenerator()
    project = generator._parse(json.dumps({
        "files": {
            "index.html": "<!doctype html><html><body><script src='app.js'></script></body></html>",
        },
        "test_command": ["python", "-m", "pytest", "-q"],
    }))
    generated_test = project.files["tests/test_generated_project.py"]
    test_path = tmp_path / "tests/test_generated_project.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "index.html").write_text(project.files["index.html"], encoding="utf-8")
    namespace = {"__file__": str(test_path)}
    exec(compile(generated_test, str(test_path), "exec"), namespace)

    try:
        namespace["test_browser_entrypoint_and_local_assets_exist"]()
    except AssertionError as exc:
        assert "app.js" in str(exc)
    else:
        raise AssertionError("Browser smoke test must reject missing local assets")

def test_large_mission_manifest_adds_browser_entrypoint_and_tests(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    calls = 0

    async def fake_call(payload: dict) -> str:
        nonlocal calls
        calls += 1
        prompt = payload["prompt"]
        if calls == 1:
            return json.dumps(
                {"files": [{"path": "app.js", "purpose": "Dashboard interactions"}]}
            )
        path = prompt.split("File to generate: ", 1)[1].splitlines()[0]
        return json.dumps({"content": f"// generated {path}"})

    generator._call = fake_call  # type: ignore[method-assign]
    project = asyncio.run(
        generator._generate_large_mission(
            "Personal Dashboard",
            "Build a browser dashboard with search, create, edit, delete, filters, and responsive layout.",
        )
    )

    assert "index.html" in project.files
    assert "style.css" in project.files
    assert "app.js" in project.files
    assert "tests/test_project.py" in project.files
    assert calls == 5



def test_small_mission_retries_transient_generation_failure() -> None:
    generator = OllamaProjectGenerator()
    calls: list[dict] = []

    async def flaky_call(payload: dict) -> str:
        calls.append(payload)
        if len(calls) == 1:
            raise RuntimeError("Ollama temporarily unavailable")
        return json.dumps({
            "files": {
                "main.py": "def normalize(value):\n    return value.strip().lower()\n",
                "tests/test_main.py": (
                    "from main import normalize\n\n"
                    "def test_normalize_trims_and_lowercases():\n"
                    "    assert normalize('  Hello  ') == 'hello'\n"
                ),
            },
            "test_command": ["python", "-m", "pytest", "-q"],
        })

    generator._call = flaky_call  # type: ignore[method-assign]
    project = asyncio.run(generator.generate("Text Normalizer", "Create a small text normalization utility."))

    assert len(calls) == 2
    assert "Recovery retry" not in calls[0]["prompt"]
    assert "Recovery retry" in calls[1]["prompt"]
    assert "main.py" in project.files
    assert "tests/test_main.py" in project.files


def test_small_mission_reports_both_failed_generation_attempts() -> None:
    generator = OllamaProjectGenerator()
    calls = 0

    async def failing_call(payload: dict) -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("Ollama timed out")

    generator._call = failing_call  # type: ignore[method-assign]
    try:
        asyncio.run(generator.generate("Text Normalizer", "Create a small text normalization utility."))
    except RuntimeError as exc:
        assert "after one recovery retry" in str(exc)
        assert "Ollama timed out" in str(exc)
    else:
        raise AssertionError("Generation must fail clearly after bounded retries")

    assert calls == 2


def test_app_named_mission_is_detected_as_browser_first() -> None:
    assert OllamaProjectGenerator._is_browser_mission(
        "Notes App: responsive HTML CSS JavaScript app with local storage"
    )
    assert OllamaProjectGenerator._is_browser_mission(
        "Personal Finance App with budgets and spending reports"
    )


def test_explicit_cli_mission_is_not_detected_as_browser_first() -> None:
    assert not OllamaProjectGenerator._is_browser_mission(
        "Build a command-line app for managing local files"
    )


def test_multi_feature_mission_uses_staged_generation_threshold() -> None:
    from src.company.project_generator import OllamaProjectGenerator

    assert OllamaProjectGenerator._is_large_mission(
        "Personal Finance App",
        "Build a personal finance app with search, filters, and export.",
    )


def test_simple_mission_stays_on_single_pass_generation() -> None:
    from src.company.project_generator import OllamaProjectGenerator

    assert not OllamaProjectGenerator._is_large_mission(
        "Text Normalizer",
        "Create a small text normalization utility.",
    )



def test_repair_prompt_preserves_browser_product_context() -> None:
    generator = OllamaProjectGenerator()
    captured: dict = {}

    async def fake_call(payload: dict) -> str:
        captured.update(payload)
        return json.dumps({
            "files": {
                "index.html": "<!doctype html><html><head><title>Study Planner</title></head><body><h1>Study Planner</h1><script src='app.js'></script></body></html>",
                "app.js": "document.title = 'Study Planner';",
                "tests/test_project.py": (
                    "def test_study_planner_default_state():\n"
                    "    sessions = []\n"
                    "    assert len(sessions) == 0\n"
                ),
            },
            "test_command": ["python", "-m", "pytest", "-q"],
        })

    generator._call = fake_call  # type: ignore[method-assign]
    repaired = asyncio.run(generator.repair(
        {
            "index.html": "<html><script src='app.js'></script></html>",
            "app.js": "document.title = 'Study Planner';",
        },
        "Project name: Study Planner\nMission objective: Build a browser study planner.\nPreview validation failure: missing style.css",
    ))

    prompt = captured["prompt"]
    assert "generated software product" in prompt
    assert "browser/web app" in prompt
    assert "Study Planner" in prompt
    assert "index.html" in repaired.files


def test_failed_large_mission_repair_clears_stale_checkpoint(tmp_path) -> None:
    from src.company.project_generator import GeneratedProject

    name = "Study Planner"
    objective = (
        "Build a browser study planner with search, create, edit, delete, "
        "and responsive layout."
    )
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    checkpoint = generator._checkpoint(name, objective)
    manifest = [
        {"path": "index.html", "purpose": "Browser entry point"},
        {"path": "style.css", "purpose": "Responsive styling"},
        {"path": "app.js", "purpose": "Planner interactions"},
        {"path": "tests/test_project.py", "purpose": "Behavioral tests"},
    ]
    files = {
        "index.html": (
            '<!doctype html><html><head><link rel="stylesheet" '
            'href="missing.css"></head><body><script src="app.js"></script></body></html>'
        ),
        "style.css": "body { font-family: sans-serif; }",
        "app.js": "document.title = 'Study Planner';",
        "tests/test_project.py": (
            "def normalize_query(value):\n"
            "    return value.strip().lower()\n\n"
            "def test_normalize_query_trims_and_lowercases():\n"
            "    assert normalize_query('  Math  ') == 'math'\n"
        ),
    }
    checkpoint.save(manifest=manifest, files=files)

    async def invalid_repair(
        current_files: dict[str, str], failure: str
    ) -> GeneratedProject:
        return GeneratedProject(
            files={
                "index.html": '<html><script src="missing.js"></script></html>',
                "style.css": "body { color: black; }",
                "app.js": "document.title = 'Study Planner';",
                "tests/test_project.py": files["tests/test_project.py"],
            },
            test_command=["python", "-m", "pytest", "-q"],
        )

    generator.repair = invalid_repair  # type: ignore[method-assign]

    try:
        asyncio.run(generator.generate(name, objective))
    except RuntimeError as exc:
        assert "after one repair" in str(exc)
        assert "missing.js" in str(exc)
    else:
        raise AssertionError("Invalid repaired output must still fail")

    assert not checkpoint.path.exists(), (
        "A failed final repair must not leave invalid generated files cached "
        "for the next automatic mission retry."
    )


def test_browser_validation_rejects_missing_asset_referenced_by_nested_css() -> None:
    from src.company.project_generator import GeneratedProject

    try:
        OllamaProjectGenerator._validate_mission_output(
            "Study Planner",
            "Build a browser app for planning study sessions.",
            GeneratedProject(
                files={
                    "index.html": '<html><link rel="stylesheet" href="assets/style.css"></html>',
                    "assets/style.css": "body { background-image: url('../images/pattern.svg'); }",
                },
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
    except RuntimeError as exc:
        assert "pattern.svg" in str(exc)
        assert "assets/style.css" in str(exc)
    else:
        raise AssertionError("Missing nested CSS assets must be rejected")


def test_browser_validation_rejects_missing_relative_javascript_module() -> None:
    from src.company.project_generator import GeneratedProject

    try:
        OllamaProjectGenerator._validate_mission_output(
            "Study Planner",
            "Build a browser app for planning study sessions.",
            GeneratedProject(
                files={
                    "index.html": '<html><script type="module" src="app.js"></script></html>',
                    "app.js": 'import { createPlanner } from "./planner.js";\ncreatePlanner();',
                },
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
    except RuntimeError as exc:
        assert "planner.js" in str(exc)
        assert "app.js" in str(exc)
    else:
        raise AssertionError("Missing local JavaScript modules must be rejected")



def test_javascript_syntax_check_preserves_esm_module_type() -> None:
    import shutil

    import pytest

    from src.company.project_generator import OllamaProjectGenerator

    if not shutil.which("node"):
        pytest.skip("Node.js is not installed")

    # Top-level await is valid in an ES module and invalid in a classic script.
    OllamaProjectGenerator._validate_javascript_syntax({
        "index.html": '<script type="module" src="app.mjs"></script>',
        "app.mjs": "await Promise.resolve();",
    })


def test_javascript_syntax_check_includes_inline_scripts() -> None:
    import shutil

    import pytest

    from src.company.project_generator import OllamaProjectGenerator

    if not shutil.which("node"):
        pytest.skip("Node.js is not installed")

    try:
        OllamaProjectGenerator._validate_javascript_syntax({
            "index.html": "<html><script>function broken( {</script></html>",
        })
    except RuntimeError as exc:
        assert "index.html:inline-script-1" in str(exc)
        assert "syntax error" in str(exc)
    else:
        raise AssertionError("Invalid inline JavaScript must be rejected")




def test_broad_product_without_tests_is_rejected() -> None:
    from src.company.project_generator import OllamaProjectGenerator

    try:
        OllamaProjectGenerator._validate_required_product_tests({
            "index.html": "<main>Inventory</main>",
            "app.js": "function addItem(items, item) { return [...items, item]; }",
        })
    except RuntimeError as exc:
        assert "no automated test files" in str(exc)
    else:
        raise AssertionError("Broad generated products without tests must be rejected")

def test_modular_planner_accepts_full_project_response_from_local_model() -> None:
    generator = OllamaProjectGenerator()
    generator._is_large_mission = lambda *_args: True  # type: ignore[method-assign]

    async def full_project_response(payload: dict) -> str:
        return json.dumps({
            "files": {
                "index.html": (
                    "<!doctype html><html><head><title>Study Planner</title>"
                    "<link rel='stylesheet' href='style.css'></head><body>"
                    "<h1>Study Planner</h1><script src='app.js'></script></body></html>"
                ),
                "style.css": "body { font-family: sans-serif; }",
                "app.js": "document.querySelector('h1').textContent = 'Study Planner';",
                "tests/test_app.py": (
                    "def test_default_study_sessions_are_empty():\n"
                    "    sessions = []\n"
                    "    assert sessions == []\n"
                ),
            },
            "test_command": ["python", "-m", "pytest", "-q"],
        })

    generator._call = full_project_response  # type: ignore[method-assign]
    project = asyncio.run(
        generator.generate(
            "Study Planner",
            "Build a browser study planner with sessions and a responsive layout.",
        )
    )

    assert "index.html" in project.files
    assert "style.css" in project.files
    assert "app.js" in project.files
    assert "tests/test_app.py" in project.files




def test_full_stack_mission_rejects_frontend_only_output() -> None:
    from src.company.project_generator import GeneratedProject

    try:
        OllamaProjectGenerator._validate_mission_output(
            "Inventory Management System",
            "Build a browser app with a backend REST API and database.",
            GeneratedProject(
                files={
                    "index.html": '<html><head><link rel="stylesheet" href="style.css"><script src="app.js"></script></head><body><h1>Inventory</h1></body></html>',
                    "style.css": "body { font-family: sans-serif; }",
                    "app.js": "document.title = 'Inventory';",
                    "tests/test_project.py": (
                        "def test_inventory_total():\n"
                        "    quantities = [2, 3]\n"
                        "    assert sum(quantities) == 5\n"
                    ),
                },
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
    except RuntimeError as exc:
        assert "no backend implementation file" in str(exc)
        assert "frontend-only" in str(exc)
    else:
        raise AssertionError("Explicit full-stack requests must not ship frontend-only output")


def test_full_stack_mission_accepts_explicit_backend_module() -> None:
    from src.company.project_generator import GeneratedProject

    OllamaProjectGenerator._validate_mission_output(
        "Inventory Management System",
        "Build a browser app with a backend REST API and database.",
        GeneratedProject(
            files={
                "index.html": '<html><head><link rel="stylesheet" href="style.css"><script src="app.js"></script></head><body><h1>Inventory</h1></body></html>',
                "style.css": "body { font-family: sans-serif; }",
                "app.js": "document.title = 'Inventory';",
                "backend/api.py": "def health():\n    return {'status': 'ok'}\n",
                "tests/test_project.py": (
                    "def test_inventory_total():\n"
                    "    quantities = [2, 3]\n"
                    "    assert sum(quantities) == 5\n"
                ),
            },
            test_command=["python", "-m", "pytest", "-q"],
        ),
    )


def test_full_stack_manifest_rejects_missing_backend_module(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    calls = 0
    manifest = {
        "files": [
            {"path": "index.html", "purpose": "Browser entry point"},
            {"path": "style.css", "purpose": "Visual styling"},
            {"path": "app.js", "purpose": "Frontend interactions"},
            {"path": "tests/test_project.py", "purpose": "Product behavior tests"},
        ]
    }

    async def fake_call(payload: dict) -> str:
        nonlocal calls
        calls += 1
        return json.dumps(manifest)

    generator._call = fake_call  # type: ignore[method-assign]

    try:
        asyncio.run(
            generator._generate_large_mission(
                "Inventory Management System",
                "Build a browser app with a backend REST API and database.",
            )
        )
    except RuntimeError as exc:
        assert "no backend implementation file" in str(exc)
        assert calls == 2
    else:
        raise AssertionError("Manifest recovery must reject a frontend-only full-stack plan")


def test_generated_python_syntax_is_checked_for_non_browser_projects() -> None:
    from src.company.project_generator import GeneratedProject

    try:
        OllamaProjectGenerator._validate_mission_output(
            "Text Utility",
            "Create a small command-line text utility.",
            GeneratedProject(
                files={"main.py": "def normalize(value):\n    return value.strip(\n"},
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
    except RuntimeError as exc:
        assert "main.py:" in str(exc)
        assert "syntax check failed" in str(exc)
    else:
        raise AssertionError("Malformed generated Python must be rejected before QA")


def test_generated_python_syntax_accepts_valid_modules() -> None:
    OllamaProjectGenerator._validate_python_syntax({
        "src/main.py": "def normalize(value):\n    return value.strip().lower()\n",
        "README.md": "This file is not Python and should not be parsed.",
    })


def test_backend_request_detection_respects_explicit_frontend_only_constraints() -> None:
    assert not OllamaProjectGenerator._mission_requires_backend(
        "Build a browser app with local storage and no backend or database."
    )
    assert not OllamaProjectGenerator._mission_requires_backend(
        "Build a frontend-only expense tracker without a database."
    )
    assert OllamaProjectGenerator._mission_requires_backend(
        "Build an inventory app with a backend API and no database."
    )


def test_full_stack_mission_accepts_common_routes_module_layout() -> None:
    from src.company.project_generator import GeneratedProject

    OllamaProjectGenerator._validate_mission_output(
        "Inventory Management System",
        "Build a browser app with a backend REST API and database.",
        GeneratedProject(
            files={
                "index.html": '<html><body><script src="app.js"></script></body></html>',
                "app.js": "document.title = 'Inventory';",
                "src/routes.py": "def health():\n    return {'status': 'ok'}\n",
                "tests/test_project.py": (
                    "def test_inventory_total():\n"
                    "    quantities = [2, 3]\n"
                    "    assert sum(quantities) == 5\n"
                ),
            },
            test_command=["python", "-m", "pytest", "-q"],
        ),
    )


def test_backend_validation_accepts_express_server_in_generic_entrypoint() -> None:
    from src.company.project_generator import GeneratedProject

    OllamaProjectGenerator._validate_mission_output(
        "Appointment Service API",
        "Build a REST API for managing appointments.",
        GeneratedProject(
            files={
                "index.js": (
                    "const express = require('express');\n"
                    "const app = express();\n"
                    "app.get('/appointments', (_req, res) => res.json([]));\n"
                    "app.listen(3000);\n"
                ),
                "tests/test_api.py": (
                    "from pathlib import Path\n\n"
                    "def test_appointment_api_has_route():\n"
                    "    source = (Path(__file__).resolve().parents[1] / 'index.js').read_text()\n"
                    "    assert 'express()' in source\n"
                    "    assert \"app.get('/appointments'\" in source\n"
                ),
            },
            test_command=["python", "-m", "pytest", "-q"],
        ),
    )



def test_backend_validation_accepts_modern_server_framework_signatures() -> None:
    from src.company.project_generator import GeneratedProject

    server_sources = (
        ("hono.js", "const app = new Hono();\\napp.get('/health', (c) => c.text('ok'));", "Hono"),
        ("main.ts", "const app = await NestFactory.create(AppModule);", "NestFactory.create"),
        ("server.js", "Bun.serve({ port: 3000, fetch: () => new Response('ok') });", "Bun.serve"),
        ("main.ts", "Deno.serve(() => new Response('ok'));", "Deno.serve"),
    )
    for path, source, signature in server_sources:
        OllamaProjectGenerator._validate_mission_output(
            "Service API",
            "Build a REST API service.",
            GeneratedProject(
                files={
                    path: source,
                    "tests/test_api.py": (
                        "def test_api_uses_server_signature():\\n"
                        f"    source = {source!r}\\n"
                        f"    assert {signature!r} in source\\n"
                    ),
                },
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )
