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
                    "tests/test_app.py": "def test_expense_tracker_title():\n    assert 'Expense Tracker' in 'Expense Tracker'\n",
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
