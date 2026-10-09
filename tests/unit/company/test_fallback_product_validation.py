from __future__ import annotations

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
