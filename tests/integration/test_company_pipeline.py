from pathlib import Path

import pytest

from src.agents.models.contracts import AgentDefinition, AgentResult
from src.agents.models.enums import AgentPermission
from src.agents.registry.registry import AgentRegistry
from src.company.execution.pipeline import CompanyExecutionPipeline
from src.github.automation.automation import GitHubAutomation
from src.github.client.memory import InMemoryGitHubClient
from src.github.models.contracts import GitHubRepository
from src.manager.manager import MasterManager
from src.manager.models.contracts import Mission, TaskPlanItem
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


@pytest.mark.asyncio
async def test_company_pipeline_completes_project(tmp_path: Path):
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

    manager = MasterManager(
        agent_registry=registry,
    )

    github_client = InMemoryGitHubClient()
    github = GitHubAutomation(github_client)

    pipeline = CompanyExecutionPipeline(
        project_engine=ProjectEngine(),
        manager=manager,
        qa_runner=QARunner(),
        reviewer=CodeReviewer(),
        github=github,
        memory=MemoryService(),
    )

    project_request = ProjectCreateRequest(
        name="Pipeline Test",
        description="Integration test project",
        objective="Verify the autonomous company execution pipeline",
    )

    mission = Mission(
        name="Pipeline Mission",
        objective="Complete the integration test",
        project_id="temporary",
    )

    tasks = [
        TaskPlanItem(
            title="Implement feature",
            description="Implement the requested feature",
            priority="high",
        ),
    ]

    qa_request = QATestRequest(
        command=[
            "python",
            "-c",
            "print('tests passed')",
        ],
        working_directory=str(tmp_path),
    )

    result = await pipeline.execute(
        project_request=project_request,
        mission=mission,
        tasks=tasks,
        qa_request=qa_request,
        files={
            "example.py": "def hello():\n    return 'hello'\n",
        },
        agent_executor=FakeAgentExecutor(),
        github_repository=GitHubRepository(
            owner="test-owner",
            name="test-repo",
        ),
        pull_request_head="feature/pipeline-test",
    )

    assert result.project.status.value == "completed"
    assert len(result.task_ids) == 1
    assert result.qa_result.status.value == "passed"
    assert result.review_result.status.value == "approved"
    assert result.memory_id is not None
    assert result.github_message is not None