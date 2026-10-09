from __future__ import annotations

import pytest

from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.workspace import ProjectExecutionService


def make_plan():
    return build_mission_plan(
        CompanyMission(name="Notes App", objective="Build a searchable notes app")
    )


def step(plan, name):
    return next(item for item in plan.steps if item.stage.value == name)


def test_progress_marks_active_stage_and_persists_diagnostic_detail():
    plan = make_plan()

    FactoryAutonomousRunner._record_stage_progress(
        plan, "research", "running", "Research started."
    )

    research = step(plan, "research")
    assert research.status == "running"
    assert research.attempts == 1
    assert research.detail == "Research started."


def test_engineering_progress_does_not_mark_qa_and_security_running_early():
    plan = make_plan()

    FactoryAutonomousRunner._record_stage_progress(
        plan,
        "engineering_qa_security_github",
        "running",
        "Engineering pipeline started.",
    )

    assert step(plan, "tasks").status == "running"
    assert step(plan, "agents").status == "running"
    assert step(plan, "execution").status == "running"
    assert step(plan, "qa").status == "planned"
    assert step(plan, "security").status == "planned"
    assert step(plan, "github").status == "planned"


def test_qa_failure_is_attributed_to_qa_and_preserves_completed_work():
    plan = make_plan()

    FactoryAutonomousRunner._record_stage_progress(
        plan,
        "engineering_qa_security_github",
        "running",
        "Engineering pipeline started.",
    )
    FactoryAutonomousRunner._record_stage_progress(
        plan,
        "engineering_qa_security_github",
        "failed",
        "QA failed for project demo: assertion failed",
    )

    assert step(plan, "tasks").status == "completed"
    assert step(plan, "agents").status == "completed"
    assert step(plan, "execution").status == "completed"
    assert step(plan, "qa").status == "failed"
    assert "QA failed" in step(plan, "qa").detail
    assert step(plan, "security").status == "planned"
    assert step(plan, "github").status == "planned"


@pytest.mark.asyncio
async def test_generation_failure_is_recorded_on_execution_step(tmp_path):
    class Runner:
        async def run(self, request):
            raise AssertionError("runner should not start when generation fails")

    def fail_request_builder(mission, plan):
        raise RuntimeError("Ollama timed out while generating app.js")

    adapter = FactoryAutonomousRunner(
        Runner(),
        fail_request_builder,
        workspace_service=ProjectExecutionService(tmp_path),
    )
    plan = make_plan()
    mission = CompanyMission(name="Notes App", objective="Build a searchable notes app")

    with pytest.raises(RuntimeError, match="Ollama timed out"):
        await adapter.run(mission, plan)

    execution = step(plan, "execution")
    assert execution.status == "failed"
    assert "Ollama timed out" in execution.detail
