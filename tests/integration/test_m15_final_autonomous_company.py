from pathlib import Path

import pytest

from src.manager.models.contracts import Mission, TaskPlanItem
from src.projects.models.contracts import ProjectCreateRequest
from src.qa.models.contracts import QATestRequest
from tests.integration.test_company_pipeline_failures import (
    FakeAgentExecutor,
    build_pipeline,
)


def make_request(tmp_path: Path) -> dict:
    return {
        "project_request": ProjectCreateRequest(
            name="M15 Final Autonomous Company Test",
            description="Final end-to-end autonomous company acceptance test",
            objective="Verify the complete autonomous software factory pipeline",
        ),
        "mission": Mission(
            name="M15 Final Mission",
            objective="Execute a complete autonomous software company run",
            project_id="temporary",
        ),
        "tasks": [
            TaskPlanItem(
                title="Implement feature",
                description="Implement and validate the requested feature",
                priority="high",
            )
        ],
        "qa_request": QATestRequest(
            command=[
                "python",
                "-c",
                "print('M15 autonomous QA passed')",
            ],
            working_directory=str(tmp_path),
        ),
        "files": {
            "m15_acceptance.py": (
                "def autonomous_company():\n"
                "    return True\n"
            )
        },
        "agent_executor": FakeAgentExecutor(),
    }


def events_for_run(pipeline, run_id: str) -> list:
    return [
        event
        for event in pipeline.event_service.list_events()
        if event.payload.get("run_id") == run_id
    ]


def get_completed_run_id(pipeline) -> str:
    completed = [
        event
        for event in pipeline.event_service.list_events()
        if event.event_type == "autonomous.run.completed"
        and event.payload.get("run_id")
    ]

    assert completed, "No completed autonomous run event was emitted."

    return completed[-1].payload["run_id"]


def get_failed_run_id(pipeline) -> str:
    failed = [
        event
        for event in pipeline.event_service.list_events()
        if event.event_type == "autonomous.run.failed"
        and event.payload.get("run_id")
    ]

    assert failed, "No failed autonomous run event was emitted."

    return failed[-1].payload["run_id"]


@pytest.mark.asyncio
async def test_m15_final_autonomous_company_success(tmp_path: Path) -> None:
    pipeline = build_pipeline()

    result = await pipeline.run_end_to_end(
        **make_request(tmp_path),
    )

    assert result.project.status.value == "completed"
    assert result.task_ids
    assert result.memory_id

    run_id = get_completed_run_id(pipeline)
    events = events_for_run(pipeline, run_id)

    event_types = {
        event.event_type
        for event in events
    }

    assert "project.execution.started" in event_types
    assert "project.execution.completed" in event_types
    assert "autonomous.run.completed" in event_types

    completed = [
        event
        for event in events
        if event.event_type == "autonomous.run.completed"
    ]

    assert len(completed) == 1
    assert completed[0].payload["status"] == "completed"
    assert completed[0].payload["task_count"] == len(result.task_ids)

    assert hasattr(pipeline, "observability")

    records = pipeline.observability.records(run_id)
    metrics = pipeline.observability.metrics(run_id)

    assert records
    assert all(record.run_id == run_id for record in records)
    assert metrics["events"] == len(records)
    assert metrics["completed"] == 1
    assert metrics["failures"] == 0
    assert metrics["recoveries"] == 0


@pytest.mark.asyncio
async def test_m15_final_autonomous_company_recovers_and_completes(
    tmp_path: Path,
) -> None:
    pipeline = build_pipeline()

    class FlakyReviewer:
        def __init__(self) -> None:
            self.calls = 0

        def review(self, request):
            self.calls += 1

            if self.calls < 3:
                raise RuntimeError("M15 transient review failure")

            return type(
                "ReviewResult",
                (),
                {
                    "status": type(
                        "Status",
                        (),
                        {"value": "approved"},
                    )(),
                    "summary": "Review approved",
                },
            )()

    pipeline.reviewer = FlakyReviewer()

    result = await pipeline.run_end_to_end(
        **make_request(tmp_path),
    )

    assert result.project.status.value == "completed"

    run_id = get_completed_run_id(pipeline)
    events = events_for_run(pipeline, run_id)

    failed = [
        event
        for event in events
        if event.event_type == "autonomous.run.failed"
    ]

    recovery = [
        event
        for event in events
        if event.event_type == "autonomous.run.recovery_available"
    ]

    completed = [
        event
        for event in events
        if event.event_type == "autonomous.run.completed"
    ]

    assert len(failed) == 2
    assert [event.payload["attempt"] for event in failed] == [1, 2]
    assert [
        event.payload["recovery_action"]
        for event in failed
    ] == ["retry", "retry"]

    assert all(
        event.payload["retryable"] is True
        for event in failed
    )

    assert len(recovery) == 2
    assert [
        event.payload["attempt"]
        for event in recovery
    ] == [1, 2]

    assert len(completed) == 1

    metrics = pipeline.observability.metrics(run_id)

    assert metrics["failures"] == 2
    assert metrics["recoveries"] == 2
    assert metrics["completed"] == 1


@pytest.mark.asyncio
async def test_m15_final_autonomous_company_blocks_permanent_failure(
    tmp_path: Path,
) -> None:
    pipeline = build_pipeline()

    class FailingReviewer:
        def review(self, request):
            raise RuntimeError("M15 permanent review failure")

    pipeline.reviewer = FailingReviewer()

    with pytest.raises(
        RuntimeError,
        match="M15 permanent review failure",
    ):
        await pipeline.run_end_to_end(
            **make_request(tmp_path),
        )

    run_id = get_failed_run_id(pipeline)
    events = events_for_run(pipeline, run_id)

    failed = [
        event
        for event in events
        if event.event_type == "autonomous.run.failed"
    ]

    recovery = [
        event
        for event in events
        if event.event_type == "autonomous.run.recovery_available"
    ]

    completed = [
        event
        for event in events
        if event.event_type == "autonomous.run.completed"
    ]

    assert len(failed) == 3
    assert [
        event.payload["attempt"]
        for event in failed
    ] == [1, 2, 3]

    assert failed[-1].payload["recovery_action"] == "block"
    assert failed[-1].payload["retryable"] is False

    assert len(recovery) == 2
    assert completed == []

    metrics = pipeline.observability.metrics(run_id)

    assert metrics["failures"] == 3
    assert metrics["recoveries"] == 2
    assert metrics["completed"] == 0


def test_m15_pipeline_exposes_required_autonomous_components() -> None:
    pipeline = build_pipeline()

    required_components = [
        "project_engine",
        "manager",
        "qa_runner",
        "debugger",
        "reviewer",
        "memory",
        "recovery",
        "event_service",
        "observability",
    ]

    for component in required_components:
        assert hasattr(pipeline, component), component


@pytest.mark.asyncio
async def test_m15_run_produces_complete_audit_trail(
    tmp_path: Path,
) -> None:
    pipeline = build_pipeline()

    result = await pipeline.run_end_to_end(
        **make_request(tmp_path),
    )

    assert result.project.status.value == "completed"

    run_id = get_completed_run_id(pipeline)
    events = events_for_run(pipeline, run_id)

    completed = [
        event
        for event in events
        if event.event_type == "autonomous.run.completed"
    ]

    assert len(completed) == 1

    records = pipeline.observability.records(run_id)

    assert records

    event_types = {
        record.event_type
        for record in records
    }

    assert "project.execution.started" in event_types
    assert "project.execution.completed" in event_types
    assert "autonomous.run.completed" in event_types

    exported = pipeline.observability.export(run_id)

    assert len(exported) == len(records)
    assert all(item["run_id"] == run_id for item in exported)
    assert all(item["record_id"] for item in exported)
    assert all(item["timestamp"] for item in exported)
