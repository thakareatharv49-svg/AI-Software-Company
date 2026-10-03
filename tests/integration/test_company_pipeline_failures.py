from pathlib import Path

import pytest

from src.agents.models.contracts import AgentDefinition, AgentResult
from src.agents.models.enums import AgentPermission
from src.agents.registry.registry import AgentRegistry
from src.company.execution.pipeline import CompanyExecutionPipeline
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


def build_pipeline():
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
        memory=MemoryService(),
    )


@pytest.mark.asyncio
async def test_pipeline_blocks_when_qa_fails(tmp_path: Path):
    pipeline = build_pipeline()

    with pytest.raises(RuntimeError, match="QA failed"):
        await pipeline.execute(
            project_request=ProjectCreateRequest(
                name="QA Failure Test",
                description="Test QA failure handling",
                objective="Verify failure handling",
            ),
            mission=Mission(
                name="QA Failure Mission",
                objective="Test QA failure",
                project_id="temporary",
            ),
            tasks=[
                TaskPlanItem(
                    title="Implement feature",
                    description="Implement feature",
                    priority="high",
                )
            ],
            qa_request=QATestRequest(
                command=["python", "-c", "raise SystemExit(1)"],
                working_directory=str(tmp_path),
            ),
            files={},
            agent_executor=FakeAgentExecutor(),
        )


@pytest.mark.asyncio
async def test_pipeline_blocks_when_security_review_fails(tmp_path: Path):
    pipeline = build_pipeline()

    with pytest.raises(RuntimeError, match="Code review failed"):
        await pipeline.execute(
            project_request=ProjectCreateRequest(
                name="Security Failure Test",
                description="Test security failure handling",
                objective="Verify security failure handling",
            ),
            mission=Mission(
                name="Security Failure Mission",
                objective="Test security failure",
                project_id="temporary",
            ),
            tasks=[
                TaskPlanItem(
                    title="Implement feature",
                    description="Implement feature",
                    priority="high",
                )
            ],
            qa_request=QATestRequest(
                command=["python", "-c", "print('tests passed')"],
                working_directory=str(tmp_path),
            ),
            files={
                "unsafe.py": "import os\nos.system('dangerous command')\n",
            },
            agent_executor=FakeAgentExecutor(),
        )

