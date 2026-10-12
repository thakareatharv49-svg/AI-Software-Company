from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.agents.models.contracts import AgentDefinition, AgentResult
from src.agents.models.enums import AgentPermission
from src.agents.registry.registry import AgentRegistry
from src.company.artifact_validation import validate_generated_artifacts
from src.company.execution.pipeline import CompanyExecutionPipeline
from src.company.project_generator import OllamaProjectGenerator
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission, TaskPlanItem
from src.memory.service.service import MemoryService
from src.projects.engine.project_engine import ProjectEngine
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.execution.runner import QARunner
from src.qa.models.contracts import QATestRequest
from src.security.review.reviewer import CodeReviewer


class SuccessfulEngineer:
    async def __call__(self, request):
        return AgentResult(
            task_id=request.task_id,
            agent_name="engineer",
            success=True,
            output="Generated product files are ready for QA.",
        )


@pytest.mark.asyncio
async def test_multi_feature_expense_app_completes_factory_lifecycle(
    tmp_path: Path,
) -> None:
    """Exercise a large browser product through generation, QA, review and release."""
    objective = (
        "Build a responsive personal Expense Tracker web app with create, edit, "
        "delete and search transactions, category filters, monthly budgets, "
        "spending summaries, validation, confirmation dialogs, empty states, "
        "and persistent local storage."
    )
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path / "checkpoints")
    generated = await generator.generate("Personal Expense Tracker", objective)

    assert {"index.html", "style.css", "app.js"} <= generated.files.keys()
    assert any(path.startswith("tests/") for path in generated.files)
    assert any(
        marker in generated.files["index.html"].casefold()
        for marker in ("expense tracker", "finwise")
    )

    # A successful lifecycle must produce a self-contained browser artifact,
    # not just a directory of files that happen to exist.
    assert validate_generated_artifacts(generated.files) == []
    app_source = generated.files["app.js"]
    for feature in (
        "localStorage",
        "search",
        "delete",
        "edit",
        "budget",
        "category-filter",
        "confirm(",
    ):
        assert feature.casefold() in app_source.casefold(), (
            f"The generated Expense Tracker is missing its {feature!r} workflow."
        )

    node = shutil.which("node")
    if node:
        syntax = subprocess.run(
            [node, "--check", "-"],
            input=app_source,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert syntax.returncode == 0, (
            "Generated Expense Tracker JavaScript failed syntax validation: "
            f"{syntax.stderr or syntax.stdout}"
        )

    # Materialize the deliverable exactly as a product workspace would.
    for relative_path, file_content in generated.files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file_content, encoding="utf-8")

    registry = AgentRegistry()
    registry.register(
        AgentDefinition(
            name="engineer",
            role="software engineer",
            capabilities=["coding"],
            permissions={AgentPermission.READ_FILES, AgentPermission.WRITE_FILES},
        )
    )
    pipeline = CompanyExecutionPipeline(
        project_engine=ProjectEngine(),
        manager=MasterManager(agent_registry=registry),
        qa_runner=QARunner(),
        reviewer=CodeReviewer(),
        memory=MemoryService(),
        project_generator=generator,
    )

    result = await pipeline.run_end_to_end(
        project_request=ProjectCreateRequest(
            name="Personal Expense Tracker",
            description="A local-first, multi-feature personal finance web app.",
            objective=objective,
        ),
        mission=Mission(
            name="Personal Expense Tracker mission",
            objective=objective,
            project_id="temporary",
        ),
        tasks=[
            TaskPlanItem(
                title="Build and validate expense workflows",
                description=objective,
                priority="high",
            ),
        ],
        qa_request=QATestRequest(
            command=[sys.executable, "-m", "pytest", "-q"],
            working_directory=str(tmp_path),
        ),
        files=dict(generated.files),
        agent_executor=SuccessfulEngineer(),
    )

    assert result.project.status.value == "completed"
    assert result.qa_result.status.value == "passed"
    assert result.qa_result.exit_code == 0
    assert result.qa_result.stdout.strip(), "QA must retain evidence from the executed test command."
    assert result.qa_result.duration_ms is not None
    assert result.review_result.status.value == "approved"
    assert result.browser_preview is True
    assert result.memory_id
    assert (tmp_path / "index.html").is_file()
    assert (tmp_path / "app.js").is_file()
