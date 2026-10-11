from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.company.project_generator import OllamaProjectGenerator


# These are the deterministic offline products the factory promises to deliver
# without depending on the local Ollama service. Run each product's own QA suite
# from a clean workspace, exactly as the factory does after writing its files.
PRODUCTS = (
    (
        "Notes App",
        "Create, edit, delete, search and pin notes using browser local storage.",
    ),
    (
        "To-Do List",
        "Build a responsive To-Do List web application with add, edit, delete, complete, filters, and persistent tasks.",
    ),
    (
        "Personal Expense Tracker",
        "Build a personal expense tracker with categories, monthly budgets, and spending summaries.",
    ),
    ("Calculator", "Build a calculator with basic arithmetic"),
    ("Tic-Tac-Toe", "Build a Tic-Tac-Toe game with restart and score tracking"),
)


@pytest.mark.parametrize(("name", "objective"), PRODUCTS)
def test_deterministic_browser_product_passes_its_own_qa_suite(
    name: str,
    objective: str,
    tmp_path: Path,
) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path / "checkpoints")
    generated = asyncio.run(generator.generate(name, objective))

    assert "index.html" in generated.files, f"{name} must have a browser entry point"
    assert any(path.startswith("tests/") for path in generated.files), (
        f"{name} must include its own automated tests"
    )

    workspace = tmp_path / "product"
    workspace.mkdir()
    for relative_path, content in generated.files.items():
        target = workspace / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    command = list(generated.test_command)
    executable = Path(command[0]).name.casefold()
    if executable in {"python", "python3", "python.exe", "py", "py.exe"}:
        command[0] = sys.executable

    result = subprocess.run(
        command,
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, (
        f"{name} generated product tests failed.\n"
        f"Command: {command!r}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    node = shutil.which("node")
    if node:
        for relative_path in generated.files:
            if relative_path.endswith((".js", ".mjs", ".cjs")):
                syntax = subprocess.run(
                    [node, "--check", str(workspace / relative_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                assert syntax.returncode == 0, (
                    f"{name} has invalid JavaScript in {relative_path}: "
                    f"{syntax.stderr or syntax.stdout}"
                )
