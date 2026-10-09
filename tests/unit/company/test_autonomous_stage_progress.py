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

def test_factory_persists_stage_progress_to_the_mission_job():
    from src.company.mission_jobs import MissionJob, MissionJobStatus
    from src.company.project_factory import FactoryProject, ProjectFactory

    class Store:
        def __init__(self):
            self.projects = []

        def save(self, project):
            self.projects.append(project)

    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    mission = CompanyMission(name="Notes App", objective="Build a searchable notes app")
    plan = make_plan()
    job_store = JobStore()
    job_store.save(
        MissionJob(
            id=mission.id,
            mission=mission,
            plan=plan,
            status=MissionJobStatus.RUNNING,
            message="Running",
        )
    )
    project = FactoryProject(mission=mission, plan=plan)
    factory = ProjectFactory(
        orchestrator=object(),
        controller=object(),
        pipeline=object(),
        store=Store(),
        job_store=job_store,
    )

    FactoryAutonomousRunner._record_stage_progress(
        plan, "research", "running", "Research started."
    )
    factory._persist_plan_progress(project)

    persisted = job_store.get(mission.id)
    assert step(persisted.plan, "research").status == "running"
    assert step(persisted.plan, "research").detail == "Research started."


def test_final_acceptance_failure_marks_only_the_rejected_factory_stage():
    from types import SimpleNamespace

    plan = make_plan()
    FactoryAutonomousRunner._record_acceptance_failures(
        plan,
        [
            SimpleNamespace(
                name="qa_passed",
                detail="Generated product tests failed.",
            ),
            SimpleNamespace(
                name="security_approved",
                detail="Security review rejected an unsafe pattern.",
            ),
        ],
    )

    assert step(plan, "qa").status == "failed"
    assert "Generated product tests failed" in step(plan, "qa").detail
    assert step(plan, "security").status == "failed"
    assert "Security review rejected" in step(plan, "security").detail
    assert step(plan, "research").status == "planned"
    assert step(plan, "architecture").status == "planned"


@pytest.mark.asyncio
async def test_progress_persistence_failure_does_not_abort_autonomous_run(tmp_path):
    from types import SimpleNamespace

    from src.company.acceptance import AutonomousCompanyAcceptance

    class Stage:
        def __init__(self, name):
            self.name = name
            self.status = "completed"

    class Runner:
        async def run(self, request):
            return SimpleNamespace(
                stages=tuple(
                    Stage(name)
                    for name in AutonomousCompanyAcceptance.REQUIRED_STAGES
                ),
                ceo=SimpleNamespace(
                    decision=SimpleNamespace(requires_human=False),
                    mission=SimpleNamespace(status="approved"),
                ),
                pipeline=SimpleNamespace(
                    project=SimpleNamespace(id="telemetry-ok", name="Notes"),
                    qa_result=SimpleNamespace(status="passed"),
                    review_result=SimpleNamespace(status="approved"),
                ),
                deployment=SimpleNamespace(status="completed"),
                monitoring=SimpleNamespace(status="completed"),
                learning=SimpleNamespace(signals=[{"kind": "success"}]),
            )

    def build_request(mission, plan):
        return SimpleNamespace(
            files={},
            qa_request=None,
        )

    adapter = FactoryAutonomousRunner(
        Runner(),
        build_request,
        workspace_service=ProjectExecutionService(tmp_path),
    )
    result = await adapter.run(
        CompanyMission(name="Notes", objective="Build a notes app"),
        make_plan(),
        on_progress=lambda _plan: (_ for _ in ()).throw(RuntimeError("database offline")),
    )

    assert result.pipeline.project.id == "telemetry-ok"
