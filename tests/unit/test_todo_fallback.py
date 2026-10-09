from __future__ import annotations

import re

import pytest

from src.company.project_generator import OllamaProjectGenerator
from src.company.todo_fallback import todo_fallback_files


def test_todo_fallback_has_a_runnable_browser_entry_and_local_assets() -> None:
    files = todo_fallback_files()
    html = files["index.html"]
    assert 'href="style.css"' in html
    assert 'src="app.js"' in html
    assert {"index.html", "style.css", "app.js", "tests/test_project.py"} <= files.keys()

    for reference in re.findall(r"""(?:src|href)\s*=\s*["']([^"'#]+)["']""", html):
        if not reference.startswith(("http:", "https:", "data:")):
            assert reference in files


def test_todo_fallback_supports_crud_filters_and_persistence_without_seed_data() -> None:
    files = todo_fallback_files()
    html = files["index.html"]
    js = files["app.js"]
    for behavior in (
        "localStorage.getItem",
        "localStorage.setItem",
        "tasks.push",
        "tasks.map",
        "tasks.filter",
        'data-action="edit"',
        'data-action="delete"',
        'data-action="toggle"',
    ):
        assert behavior in js
    for filter_name in ("all", "pending", "completed"):
        assert f'data-filter="{filter_name}"' in html
    assert 'document.querySelectorAll("[data-filter]")' in js
    assert 'localStorage.getItem(STORAGE_KEY) || "[]"' in js
    assert "sampleTasks" not in js
    assert "demoTasks" not in js


@pytest.mark.asyncio
async def test_todo_mission_uses_fallback_without_calling_ollama() -> None:
    generator = OllamaProjectGenerator()

    async def unexpected_model_call(_payload: dict[str, object]) -> str:
        raise AssertionError("To-Do missions should not need slow model generation")

    generator._call = unexpected_model_call  # type: ignore[method-assign]
    result = await generator.generate(
        "To-Do List",
        "Build a responsive To-Do List web application with add, edit, delete, complete, filters, and persistent tasks.",
    )

    assert result.files["index.html"]
    assert result.files["app.js"]
    assert result.test_command == ["python", "-m", "pytest", "-q"]
