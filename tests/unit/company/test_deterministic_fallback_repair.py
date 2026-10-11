from __future__ import annotations

import pytest

from src.company.project_generator import OllamaProjectGenerator


@pytest.mark.parametrize(
    ("files", "failure", "expected_marker"),
    [
        (
            {"index.html": "<h1>All notes</h1>"},
            "QA failed: missing note edit behavior",
            "Paper — Notes for your mind",
        ),
        (
            {"index.html": "<title>Daymark — Task Manager</title>"},
            "QA failed: task completion filter",
            "daymark",
        ),
        (
            {"index.html": "<h1>Tic-Tac-Toe</h1>"},
            "QA failed: restart button",
            "Tic-Tac-Toe",
        ),
        (
            {"index.html": "<title>Expense Tracker</title>"},
            "QA failed: monthly budget",
            "Expense Tracker",
        ),
        (
            {"index.html": "<h1>Calculator</h1>"},
            "QA failed: arithmetic operation",
            "Calculator",
        ),
    ],
)
def test_supported_product_repair_has_offline_recovery(
    files: dict[str, str],
    failure: str,
    expected_marker: str,
) -> None:
    generator = OllamaProjectGenerator()
    repaired = generator._fallback_repair(files, failure)

    assert {"index.html", "style.css", "app.js"} <= repaired.files.keys()
    assert any(expected_marker.casefold() in content.casefold() for content in repaired.files.values())
    assert repaired.test_command == ["python", "-m", "pytest", "-q"]
