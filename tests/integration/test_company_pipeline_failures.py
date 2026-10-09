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




@pytest.mark.asyncio
async def test_run_end_to_end_recovers_from_transient_failure(tmp_path: Path):
    pipeline = build_pipeline()
    pipeline.event_service.clear()

    class FlakyReviewer:
        def __init__(self):
            self.calls = 0

        def review(self, request):
            self.calls += 1

            if self.calls < 3:
                raise RuntimeError("transient review failure")

            return type(
                "ReviewResult",
                (),
                {
                    "status": type("Status", (), {"value": "approved"})(),
                    "summary": "Review approved",
                },
            )()

    pipeline.reviewer = FlakyReviewer()

    result = await pipeline.run_end_to_end(
        project_request=ProjectCreateRequest(
            name="Recovery Transient Failure Test",
            description="Test autonomous recovery from transient failure",
            objective="Verify the pipeline retries and eventually completes",
        ),
        mission=Mission(
            name="Recovery Transient Failure Mission",
            objective="Test transient recovery",
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
        files={"example.py": "def example():\n    return True\n"},
        agent_executor=FakeAgentExecutor(),
    )

    events = pipeline.event_service.list_events()

    failed_events = [
        event
        for event in events
        if event.event_type == "autonomous.run.failed"
    ]

    recovery_events = [
        event
        for event in events
        if event.event_type == "autonomous.run.recovery_available"
    ]

    completed_events = [
        event
        for event in events
        if event.event_type == "autonomous.run.completed"
    ]

    assert result.project.status.value == "completed"

    assert len(failed_events) == 2
    assert [event.payload["attempt"] for event in failed_events] == [1, 2]
    assert [
        event.payload["recovery_action"] for event in failed_events
    ] == ["retry", "retry"]
    assert all(
        event.payload["retryable"] is True
        for event in failed_events
    )

    assert len(recovery_events) == 2
    assert [event.payload["attempt"] for event in recovery_events] == [1, 2]

    assert len(completed_events) == 1


@pytest.mark.asyncio
async def test_run_end_to_end_blocks_after_recovery_limit(tmp_path: Path):
    pipeline = build_pipeline()
    pipeline.event_service.clear()

    class FailingReviewer:
        def review(self, request):
            raise RuntimeError("permanent review failure")

    pipeline.reviewer = FailingReviewer()

    with pytest.raises(RuntimeError, match="permanent review failure"):
        await pipeline.run_end_to_end(
            project_request=ProjectCreateRequest(
                name="Recovery Limit Test",
                description="Test bounded autonomous recovery",
                objective="Verify recovery attempt limit",
            ),
            mission=Mission(
                name="Recovery Limit Mission",
                objective="Test recovery limit",
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
            files={"example.py": "def example():\n    return True\n"},
            agent_executor=FakeAgentExecutor(),
        )

    events = pipeline.event_service.list_events()

    failed_events = [
        event
        for event in events
        if event.event_type == "autonomous.run.failed"
    ]

    recovery_events = [
        event
        for event in events
        if event.event_type == "autonomous.run.recovery_available"
    ]

    assert len(failed_events) == 3

    assert failed_events[0].payload["attempt"] == 1
    assert failed_events[0].payload["recovery_action"] == "retry"
    assert failed_events[0].payload["retryable"] is True

    assert failed_events[1].payload["attempt"] == 2
    assert failed_events[1].payload["recovery_action"] == "retry"
    assert failed_events[1].payload["retryable"] is True

    assert failed_events[2].payload["attempt"] == 3
    assert failed_events[2].payload["recovery_action"] == "block"
    assert failed_events[2].payload["retryable"] is False

    assert len(recovery_events) == 2
    assert [event.payload["attempt"] for event in recovery_events] == [1, 2]


@pytest.mark.asyncio
async def test_run_end_to_end_creates_observability_audit_trail(tmp_path: Path):
    pipeline = build_pipeline()

    result = await pipeline.run_end_to_end(
        project_request=ProjectCreateRequest(
            name="Observability Test",
            description="Test audit trail",
            objective="Verify execution observability",
        ),
        mission=Mission(
            name="Observability Mission",
            objective="Verify audit trail",
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
        files={"example.py": "def example():\n    return True\n"},
        agent_executor=FakeAgentExecutor(),
    )

    completed = [
        event
        for event in pipeline.event_service.list_events()
        if event.event_type == "autonomous.run.completed"
    ]

    assert len(completed) == 1

    run_id = completed[0].payload["run_id"]
    records = pipeline.observability.records(run_id)
    metrics = pipeline.observability.metrics(run_id)

    assert records
    assert all(record.run_id == run_id for record in records)
    assert any(
        record.event_type == "project.execution.started"
        for record in records
    )
    assert any(
        record.event_type == "autonomous.run.completed"
        for record in records
    )
    assert metrics["events"] == len(records)
    assert metrics["completed"] == 1
    assert result.project.status.value == "completed"


def test_workspace_sync_delivers_repaired_and_new_files_without_stale_files(tmp_path: Path):
    from src.company.execution.pipeline import CompanyExecutionPipeline

    (tmp_path / "app.js").write_text("const value = 2;\\n", encoding="utf-8")
    (tmp_path / "index.html").write_text("<main>Repaired</main>\\n", encoding="utf-8")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "cache.json").write_text("{}", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dependency.js").write_text("ignored()", encoding="utf-8")

    files = {
        "app.js": "const value = 1;\\n",
        "deleted.js": "stale content",
    }

    CompanyExecutionPipeline._sync_generated_files_from_workspace(
        str(tmp_path),
        files,
    )

    assert files["app.js"] == "const value = 2;\\n"
    assert files["index.html"] == "<main>Repaired</main>\\n"
    assert "deleted.js" not in files
    assert not any(".pytest_cache" in path for path in files)
    assert not any("node_modules" in path for path in files)


def test_workspace_sync_refuses_missing_workspace(tmp_path: Path):
    from src.company.execution.pipeline import CompanyExecutionPipeline

    with pytest.raises(RuntimeError, match="workspace does not exist"):
        CompanyExecutionPipeline._sync_generated_files_from_workspace(
            str(tmp_path / "missing"),
            {"app.js": "source"},
        )
