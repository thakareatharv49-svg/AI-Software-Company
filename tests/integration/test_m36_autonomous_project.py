from __future__ import annotations

from pathlib import Path

import pytest

from company.autonomous_project import (
    AutonomousProjectRequest,
    AutonomousProjectRunner,
)
from company.ceo.models import Mission
from company.research.engine import UrlResearchProvider
from src.agents.models.contracts import AgentDefinition, AgentResult
from src.agents.models.enums import AgentPermission
from src.agents.registry.registry import AgentRegistry
from src.company.execution.pipeline import CompanyExecutionPipeline
from src.github.automation.automation import GitHubAutomation
from src.github.client.memory import InMemoryGitHubClient
from src.github.models.contracts import GitHubRepository
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission as ManagerMission, TaskPlanItem
from src.memory.service.service import MemoryService
from src.projects.engine.project_engine import ProjectEngine
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.execution.runner import QARunner
from src.qa.models.contracts import QATestRequest
from src.security.review.reviewer import CodeReviewer


class FakeAgentExecutor:
    async def __call__(self, request):
        return AgentResult(
            task_id=request.task_id,
            agent_name="engineer",
            success=True,
            output="Task completed",
        )


def build_pipeline() -> CompanyExecutionPipeline:
    registry = AgentRegistry()
    registry.register(
        AgentDefinition(
            name="engineer",
            role="software engineer",
            capabilities=["coding"],
            permissions={
                AgentPermission.READ_FILES,
                AgentPermission.WRITE_FILES,
            },
        )
    )

    return CompanyExecutionPipeline(
        project_engine=ProjectEngine(),
        manager=MasterManager(agent_registry=registry),
        qa_runner=QARunner(),
        reviewer=CodeReviewer(),
        github=GitHubAutomation(InMemoryGitHubClient()),
        memory=MemoryService(),
    )


@pytest.mark.asyncio
async def test_m36_runs_mission_to_monitored_project(tmp_path: Path) -> None:
    runner = AutonomousProjectRunner(
        research_provider=UrlResearchProvider(
            ("https://example.com/docs",),
            fetcher=lambda _url: "Research evidence for the project.",
        ),
        pipeline=build_pipeline(),
        deployment=lambda result: f"deployed {result.project.name}",
        monitoring=lambda result: f"monitoring {result.project.id}",
    )

    result = await runner.run(
        AutonomousProjectRequest(
            mission=Mission(
                mission_id="m36-demo",
                objective="Build and verify a small autonomous project",
            ),
            research_query="autonomous project",
            project_request=ProjectCreateRequest(
                name="M36 Demo",
                description="End-to-end autonomous project test",
                objective="Verify M36 orchestration",
            ),
            manager_mission=ManagerMission(
                name="M36 Demo Mission",
                objective="Complete the M36 project",
            ),
            tasks=(
                TaskPlanItem(
                    title="Implement feature",
                    description="Implement the requested feature",
                    priority="high",
                ),
            ),
            qa_request=QATestRequest(
                command=["python", "-c", "print('tests passed')"],
                working_directory=str(tmp_path),
            ),
            files={"example.py": "def hello():\n    return 'hello'\n"},
            agent_executor=FakeAgentExecutor(),
            github_repository=GitHubRepository(
                owner="test-owner",
                name="test-repo",
            ),
            pull_request_head="feature/m36-demo",
        )
    )

    assert result.ceo.mission.status.value == "approved"
    assert result.research.finding_count == 1
    assert result.handoff.recipient == "product-and-engineering"
    assert result.product_definition["research_findings"] == 1
    assert result.architecture["task_count"] == 1
    assert result.pipeline.project.status.value == "completed"
    assert result.pipeline.github_message is not None
    assert result.deployment.status.value == "completed"
    assert result.monitoring.status.value == "completed"
    assert result.learning.signals[0].subject == "execution_success_rate"
    assert result.dashboard.projects[0]["status"] == "completed"
    assert [stage.status.value for stage in result.stages].count("failed") == 0
