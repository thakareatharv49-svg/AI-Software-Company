from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from src.company.notes_fallback import notes_fallback_files
from src.company.project_generator import OllamaProjectGenerator


def test_notes_fallback_contains_complete_offline_product() -> None:
    files = notes_fallback_files()

    assert set(files) == {"index.html", "style.css", "app.js"}
    assert 'id="notes-grid"' in files["index.html"]
    assert 'id="note-dialog"' in files["index.html"]
    assert 'href="style.css"' in files["index.html"]
    assert 'src="app.js"' in files["index.html"]
    assert "localStorage.getItem(STORAGE_KEY)" in files["app.js"]
    assert "localStorage.setItem(STORAGE_KEY" in files["app.js"]
    assert 'data-action="pin"' in files["app.js"]
    assert 'data-action="delete"' in files["app.js"]
    assert 'data-action="edit"' in files["app.js"]
    assert "function visibleNotes()" in files["app.js"]
    assert "function saveFromForm(event)" in files["app.js"]
    assert "window.confirm(" in files["app.js"]
    assert "coming soon" not in files["app.js"].casefold()


@pytest.mark.asyncio
async def test_notes_app_mission_uses_deterministic_product_without_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = OllamaProjectGenerator()

    async def unexpected_model_call(payload):
        raise AssertionError("Notes App fallback should not call the model")

    monkeypatch.setattr(generator, "_call", unexpected_model_call)
    project = await generator.generate(
        "Notes App",
        "Create, edit, delete, search and pin notes using browser local storage.",
    )

    assert set(project.files) == {"index.html", "style.css", "app.js"}
    assert "Paper — Notes for your mind" in project.files["index.html"]
    assert "localStorage" in project.files["app.js"]


def test_notes_fallback_javascript_parses_when_node_is_available(tmp_path: Path) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed")
    script = tmp_path / "app.js"
    script.write_text(notes_fallback_files()["app.js"], encoding="utf-8")
    result = subprocess.run(
        [node, "--check", str(script)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
