from pathlib import Path
from types import SimpleNamespace

import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import ProjectFactory


class FakeRuntime:
    async def generate(self, request):
        return ModelResponse(
            content="stage completed",
            model="fake",
            provider="fake",
        )


@pytest.mark.asyncio
async def test_factory_runs_projects_sequentially() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)

    first = factory.enqueue(CompanyMission(name="One", objective="Build one"))
    second = factory.enqueue(CompanyMission(name="Two", objective="Build two"))

    results = await factory.run(max_projects=2, max_stages=12)

    assert first.status == "completed"
    assert second.status == "completed"
    assert len(results) == 2
    assert orchestrator.state.status.value == "stopped"
    assert orchestrator.state.completed_projects == 2
    assert orchestrator.state.completed_tasks == 24


@pytest.mark.asyncio
async def test_factory_continues_after_blocked_project() -> None:
    class FailingRuntime:
        async def generate(self, request):
            raise RuntimeError("model unavailable")

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FailingRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)

    project = factory.enqueue(CompanyMission(name="Blocked", objective="Fail safely"))
    later = factory.enqueue(CompanyMission(name="Later", objective="Should also be attempted"))

    results = await factory.run(max_projects=2, max_retries=0)

    assert project.status == "blocked"
    assert later.status == "blocked"
    assert len(results) == 2
    assert orchestrator.state.status.value == "blocked"


@pytest.mark.asyncio
async def test_factory_can_pause_and_resume_a_project() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(orchestrator, controller, pipeline)
    project = factory.enqueue(CompanyMission(name="Resume", objective="Build resume-safe project"))

    paused = await factory.run_next(max_stages=2)

    assert paused is project
    assert project.status == "queued"
    assert project.stages_executed == 2
    assert len(factory.queue) == 1
    assert project.plan.steps[0].status == "completed"
    assert project.plan.steps[2].status == "planned"

    resumed = await factory.run_next(max_stages=10)

    assert resumed is project
    assert project.status == "completed"
    assert project.stages_executed == 12
    assert len(factory.queue) == 0


@pytest.mark.asyncio
async def test_factory_restores_pending_projects() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    mission = CompanyMission(name="Persisted", objective="Restore me")
    plan = controller.start(mission)[0]

    class Store:
        def load_pending(self):
            return [{"mission": mission, "plan": plan, "status": "queued", "stages_executed": 4}]

        def save(self, project):
            pass

    factory = ProjectFactory(orchestrator, controller, pipeline, store=Store())

    assert factory.restore() == 1
    assert factory.queue[0].mission.id == mission.id
    assert factory.queue[0].stages_executed == 4


@pytest.mark.asyncio
async def test_factory_retries_a_failed_project() -> None:
    class RecoveringRuntime:
        calls = 0
        async def generate(self, request):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary model failure")
            return ModelResponse(content="stage completed", model="fake", provider="fake")

    runtime = RecoveringRuntime()
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(orchestrator, AgentExecutor(runtime), AgentRegistry())
    factory = ProjectFactory(orchestrator, controller, pipeline)
    project = factory.enqueue(CompanyMission(name="Retry", objective="Recover"))

    result = await factory.run(max_projects=1, max_stages=12, max_retries=1)

    assert result == [project]
    assert project.status == "completed"
    assert project.attempts == 2



@pytest.mark.asyncio
async def test_automatic_retry_includes_previous_failure_as_recovery_feedback() -> None:
    class FailOnceRunner:
        def __init__(self):
            self.objectives = []

        async def run(self, mission, plan, on_progress=None):
            self.objectives.append(mission.objective)
            if len(self.objectives) == 1:
                raise RuntimeError("QA failed: missing transaction validation")
            return SimpleNamespace(pipeline=object(), stages=[])

    runner = FailOnceRunner()
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=runner,
    )
    project = factory.enqueue(
        CompanyMission(
            name="Expense Tracker",
            objective="Build an expense tracker with transaction validation",
        )
    )

    result = await factory.run(max_projects=1, max_retries=1)

    assert result == [project]
    assert project.status == "completed"
    assert project.attempts == 2
    assert "Build an expense tracker with transaction validation" in runner.objectives[1]
    assert "missing transaction validation" in runner.objectives[1]
    assert "preserving all original mission requirements" in runner.objectives[1]
    # Recovery feedback is scoped to the retry prompt; the saved user mission
    # remains unchanged for history and future revisions.
    assert project.mission.objective == "Build an expense tracker with transaction validation"


@pytest.mark.asyncio
async def test_factory_rejects_duplicate_run() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(orchestrator, AgentExecutor(FakeRuntime()), AgentRegistry())
    factory = ProjectFactory(orchestrator, controller, pipeline)
    factory._running = True

    with pytest.raises(RuntimeError, match="already running"):
        await factory.run()



@pytest.mark.asyncio
async def test_factory_persists_mission_job_lifecycle() -> None:
    from src.company.mission_jobs import MissionJobStatus

    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    store = JobStore()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        job_store=store,
    )
    mission = CompanyMission(name="Lifecycle", objective="Persist lifecycle")
    project = factory.enqueue(mission)

    assert store.jobs[mission.id].status == MissionJobStatus.QUEUED

    result = await factory.run(max_projects=1, max_stages=12, max_retries=0)

    assert result == [project]
    assert store.jobs[mission.id].status == MissionJobStatus.COMPLETED
    assert store.jobs[mission.id].attempts == 1


@pytest.mark.asyncio
async def test_factory_rejects_duplicate_persistent_mission() -> None:
    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    store = JobStore()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        job_store=store,
    )
    mission = CompanyMission(name="Duplicate", objective="Reject duplicate")
    factory.enqueue(mission)

    with pytest.raises(ValueError, match="already has lifecycle state"):
        factory.enqueue(mission)


def test_factory_can_cancel_queued_mission() -> None:
    from src.company.mission_jobs import MissionJobStatus

    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(orchestrator, AgentExecutor(FakeRuntime()), AgentRegistry())
    store = JobStore()
    factory = ProjectFactory(orchestrator, controller, pipeline, job_store=store)
    mission = CompanyMission(name="Cancel", objective="Cancel safely")
    factory.enqueue(mission)

    job = factory.cancel(mission.id)

    assert job.status == MissionJobStatus.CANCELLED
    assert factory.queue == []


def test_factory_can_retry_blocked_mission() -> None:
    from src.company.mission_jobs import MissionJobStatus

    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(orchestrator, AgentExecutor(FakeRuntime()), AgentRegistry())
    store = JobStore()
    factory = ProjectFactory(orchestrator, controller, pipeline, job_store=store)
    mission = CompanyMission(name="Retry", objective="Retry safely")
    factory.enqueue(mission)
    job = store.jobs[mission.id]
    store.jobs[mission.id] = job.model_copy(update={"status": MissionJobStatus.BLOCKED})

    retried = factory.retry(mission.id)

    assert retried.status == MissionJobStatus.QUEUED
    assert factory.queue[0].mission.id == mission.id


@pytest.mark.asyncio
async def test_factory_records_project_output_manifest() -> None:
    class OutputStore:
        def __init__(self):
            self.manifests = []

        def save(self, manifest):
            self.manifests.append(manifest)

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    output_store = OutputStore()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        output_store=output_store,
    )
    mission = CompanyMission(name="Output", objective="Record output")

    project = factory.enqueue(mission)
    result = await factory.run(max_projects=1, max_stages=12, max_retries=0)

    assert result == [project]
    assert len(output_store.manifests) == 1
    assert output_store.manifests[0].mission_id == mission.id
    assert output_store.manifests[0].project_id == f"project:{mission.id}"
    assert output_store.manifests[0].status == "completed"


@pytest.mark.asyncio
async def test_factory_can_use_real_m36_runner_adapter() -> None:
    from src.company.autonomous_factory_runner import FactoryAutonomousRunner
    from src.company.autonomous_project import AutonomousProjectRequest
    from src.company.project_outputs import ProjectOutputManifest

    from types import SimpleNamespace

    from company.acceptance import AutonomousCompanyAcceptance

    class Stage:
        def __init__(self, name: str, status: str):
            self.name = name
            self.status = status

    class Project:
        id = "real-project-1"
        name = "Real M36"
        repository = "owner/real-project"

    class Pipeline:
        project = Project()
        qa_result = SimpleNamespace(status=SimpleNamespace(value="passed"))
        review_result = SimpleNamespace(status=SimpleNamespace(value="approved"))
        github_message = "pull request created"
        memory_id = "memory-1"

    class Result:
        # Simulate a result that satisfies the same lifecycle acceptance contract.
        stages = tuple(
            Stage(name, "COMPLETED")
            for name in AutonomousCompanyAcceptance.REQUIRED_STAGES
        )
        ceo = SimpleNamespace(
            decision=SimpleNamespace(requires_human=False),
            mission=SimpleNamespace(status=SimpleNamespace(value="approved")),
        )
        pipeline = Pipeline()
        deployment = SimpleNamespace(status=SimpleNamespace(value="completed"))
        monitoring = SimpleNamespace(status=SimpleNamespace(value="completed"))
        learning = SimpleNamespace(signals=[{"kind": "success"}])

    class Runner:
        async def run(self, request: AutonomousProjectRequest):
            assert request.mission.mission_id == mission.id
            return Result()

    def build_request(mission, plan):
        from company.ceo.models import Mission as CEOMission

        return AutonomousProjectRequest.model_construct(
            mission=CEOMission(mission_id=mission.id, objective=mission.objective),
            research_query=mission.objective,
            project_request=None,
            manager_mission=None,
            tasks=(),
            qa_request=None,
            files={"README.md": "Generated by test fixture.\n"},
        )

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    adapter = FactoryAutonomousRunner(Runner(), build_request)
    class OutputStore:
        def __init__(self):
            self.manifests: list[ProjectOutputManifest] = []
        def save(self, manifest):
            self.manifests.append(manifest)

    output_store = OutputStore()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        output_store=output_store,
        autonomous_runner=adapter,
    )
    mission = CompanyMission(name="Real M36", objective="Run real lifecycle")
    project = factory.enqueue(mission)

    result = await factory.run(max_projects=1, max_stages=12, max_retries=0)

    assert result == [project]
    assert project.status == "completed"
    assert project.stages_executed == len(AutonomousCompanyAcceptance.REQUIRED_STAGES)
    assert output_store.manifests[0].project_id == "real-project-1"
    assert output_store.manifests[0].repository == "owner/real-project"
    assert output_store.manifests[0].github_message == "pull request created"
    assert output_store.manifests[0].memory_id == "memory-1"


@pytest.mark.asyncio
async def test_factory_autonomous_runner_materializes_project_workspace(tmp_path) -> None:
    from src.company.autonomous_factory_runner import FactoryAutonomousRunner
    from src.company.autonomous_project import AutonomousProjectRequest
    from src.company.workspace import ProjectExecutionService
    from src.qa.models.contracts import QATestRequest

    from types import SimpleNamespace

    from company.acceptance import AutonomousCompanyAcceptance

    class Stage:
        def __init__(self, name: str, status: str):
            self.name = name
            self.status = status

    class Pipeline:
        project = type(
            "Project",
            (),
            {"id": "workspace-project", "name": "Workspace", "repository": None},
        )()
        qa_result = SimpleNamespace(status=SimpleNamespace(value="passed"))
        review_result = SimpleNamespace(status=SimpleNamespace(value="approved"))
        github_message = None
        memory_id = None

    class Result:
        stages = tuple(
            Stage(name, "completed")
            for name in AutonomousCompanyAcceptance.REQUIRED_STAGES
        )
        ceo = SimpleNamespace(
            decision=SimpleNamespace(requires_human=False),
            mission=SimpleNamespace(status=SimpleNamespace(value="approved")),
        )
        pipeline = Pipeline()
        deployment = SimpleNamespace(status=SimpleNamespace(value="completed"))
        monitoring = SimpleNamespace(status=SimpleNamespace(value="completed"))
        learning = SimpleNamespace(signals=[{"kind": "success"}])

    class Runner:
        async def run(self, request: AutonomousProjectRequest):
            workspace = Path(request.qa_request.working_directory)
            assert workspace.is_dir()
            assert (workspace / "src" / "main.py").read_text(encoding="utf-8") == "print('hello')"
            return Result()

    def build_request(mission, plan):
        from company.ceo.models import Mission as CEOMission

        return AutonomousProjectRequest.model_construct(
            mission=CEOMission(mission_id=mission.id, objective=mission.objective),
            research_query=mission.objective,
            project_request=None,
            manager_mission=None,
            tasks=(),
            qa_request=QATestRequest(
                command=["python", "-c", "print('ok')"],
                working_directory="unused",
            ),
            files={"src/main.py": "print('hello')"},
        )

    service = ProjectExecutionService(tmp_path)
    adapter = FactoryAutonomousRunner(
        Runner(),
        build_request,
        workspace_service=service,
    )

    mission = CompanyMission(name="Workspace", objective="Execute in isolation")
    plan = build_mission_plan(mission)

    result = await adapter.run(mission, plan)

    assert result.pipeline.project.id == "workspace-project"
    workspace = next(tmp_path.iterdir())
    assert (workspace / "src" / "main.py").read_text(encoding="utf-8") == "print('hello')"


@pytest.mark.asyncio
async def test_factory_trusts_successful_pipeline_over_stale_stage_telemetry() -> None:
    class Stage:
        def __init__(self, status: str):
            self.status = status

    class Pipeline:
        project = type("Project", (), {"id": "successful-pipeline", "repository": None})()

    class Result:
        # A successful pipeline is authoritative even if an adapter returns
        # stale failure telemetry for individual lifecycle stages.
        stages = (Stage("failed"),)
        pipeline = Pipeline()

    class Runner:
        async def run(self, mission, plan):
            return Result()

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=Runner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Calculator", objective="Build a calculator")
    )

    results = await factory.run(max_projects=1, max_retries=0)

    assert results == [project]
    assert project.status == "completed"
    assert project.last_error is None


@pytest.mark.asyncio
async def test_factory_preserves_pipeline_result_when_stage_telemetry_is_malformed() -> None:
    class BrokenStage:
        @property
        def status(self):
            raise RuntimeError("telemetry unavailable")

    class Pipeline:
        project = type("Project", (), {"id": "pipeline-ok", "repository": None})()

    class Result:
        stages = (BrokenStage(),)
        pipeline = Pipeline()

    class Runner:
        async def run(self, mission, plan):
            return Result()

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=Runner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Calculator", objective="Build a calculator")
    )

    results = await factory.run(max_projects=1, max_retries=0)

    assert results == [project]
    assert project.status == "completed"
    assert project.last_error is None

@pytest.mark.asyncio
async def test_factory_persists_pre_progress_failure_stage() -> None:
    class FailingAutonomousRunner:
        async def run(self, mission, plan):
            raise RuntimeError("request setup exploded")

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=FailingAutonomousRunner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Large mission", objective="Build a multi-feature web app")
    )

    await factory.run(max_projects=1, max_retries=0)

    failed_steps = [step for step in project.plan.steps if step.status == "failed"]
    assert len(failed_steps) == 1
    assert failed_steps[0].detail == "RuntimeError: request setup exploded"
    assert project.last_error == "RuntimeError: request setup exploded"


@pytest.mark.asyncio
async def test_workspace_preparation_failure_is_recorded_as_execution_failure() -> None:
    mission = CompanyMission(name="Workspace failure", objective="Build a web app")
    plan = build_mission_plan(mission)

    class BrokenWorkspaceService:
        def create_workspace(self, mission_id: str):
            raise OSError("workspace disk is unavailable")

    class UnusedRunner:
        async def run(self, request):
            raise AssertionError("runner must not start without a workspace")

    adapter = FactoryAutonomousRunner(
        runner=UnusedRunner(),
        request_builder=lambda _mission, _plan: SimpleNamespace(
            files={"index.html": "<main>App</main>"},
            qa_request=None,
        ),
        workspace_service=BrokenWorkspaceService(),
    )
    persisted_plans = []

    with pytest.raises(OSError, match="workspace disk is unavailable"):
        await adapter.run(
            mission,
            plan,
            on_progress=lambda current_plan: persisted_plans.append(
                current_plan.model_copy(deep=True)
            ),
        )

    execution = next(step for step in plan.steps if step.stage.value == "execution")
    assert execution.status == "failed"
    assert "Workspace preparation failed" in execution.detail
    assert "workspace disk is unavailable" in execution.detail
    assert persisted_plans
    assert next(
        step for step in persisted_plans[-1].steps if step.stage.value == "execution"
    ).status == "failed"


@pytest.mark.asyncio
async def test_autonomous_startup_failure_is_attributed_to_execution() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )

    def fail_start(_mission):
        raise RuntimeError("orchestrator startup unavailable")

    controller.start = fail_start
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=object(),
    )
    project = factory.enqueue(
        CompanyMission(name="Startup failure", objective="Build a notes app")
    )

    result = await factory.run_next(max_retries=0)

    assert result is project
    assert project.status == "blocked"
    assert project.last_error is not None
    assert "orchestrator startup unavailable" in project.last_error
    execution = next(step for step in project.plan.steps if step.stage.value == "execution")
    research = next(step for step in project.plan.steps if step.stage.value == "research")
    assert execution.status == "failed"
    assert "orchestrator startup unavailable" in execution.detail
    assert research.status == "planned"

def test_manual_retry_resets_failed_plan_stages_and_persists_reset() -> None:
    from src.company.mission_jobs import MissionJob, MissionJobStatus

    class JobStore:
        def __init__(self):
            self.jobs = {}

        def get(self, job_id):
            return self.jobs.get(job_id)

        def save(self, job):
            self.jobs[job.id] = job

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    mission = CompanyMission(name="Retry stale plan", objective="Build a working notes app")
    plan = build_mission_plan(mission)
    failed_step = plan.steps[0]
    failed_step.status = "failed"
    failed_step.detail = "Previous attempt failed"
    completed_step = plan.steps[1]
    completed_step.status = "completed"
    completed_step.detail = "Completed in previous attempt"
    store = JobStore()
    store.jobs[mission.id] = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.BLOCKED,
        message="Previous attempt blocked",
        attempts=1,
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        job_store=store,
    )

    factory.retry(mission.id)

    queued_project = factory.queue[0]
    persisted_job = store.jobs[mission.id]
    assert queued_project.retry_feedback == "Previous attempt failed"
    assert queued_project.plan.steps[0].status == "planned"
    assert queued_project.plan.steps[0].detail is None
    assert persisted_job.plan.steps[0].status == "planned"
    assert persisted_job.plan.steps[0].detail is None
    assert queued_project.plan.steps[1].status == "planned"
    assert queued_project.plan.steps[1].detail is None
    assert persisted_job.plan.steps[1].status == "planned"
    assert persisted_job.plan.steps[1].detail is None


def test_automatic_retry_resets_completed_and_failed_stage_progress():
    from src.company.project_factory import FactoryProject

    mission = CompanyMission(
        name="Automatic retry",
        objective="Build a multi-feature web app",
    )
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "Completed on the failed attempt"
    plan.steps[1].status = "failed"
    plan.steps[1].detail = "QA failed on the previous attempt"
    plan.steps[2].status = "running"
    plan.steps[2].detail = "Was running when the attempt failed"

    orchestrator = CompanyOrchestrator()
    factory = ProjectFactory(
        orchestrator,
        MissionController(orchestrator),
        MissionExecutionPipeline(
            orchestrator,
            AgentExecutor(FakeRuntime()),
            AgentRegistry(),
        ),
    )
    project = FactoryProject(mission=mission, plan=plan, last_error="previous failure")

    factory._reset_for_retry(project, reset_completed=True)

    assert project.last_error is None
    assert all(step.status == "planned" for step in project.plan.steps)
    assert all(step.detail is None for step in project.plan.steps)



@pytest.mark.asyncio
async def test_previous_mission_result_cannot_mask_next_mission_failure() -> None:
    class FailingAutonomousRunner:
        async def run(self, mission, plan, on_progress=None):
            raise RuntimeError("request preparation failed")

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=FailingAutonomousRunner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Second mission", objective="Fail before pipeline starts")
    )
    # Simulate a successful result retained from the previously completed mission.
    factory._last_autonomous_result = SimpleNamespace(pipeline=object())

    result = await factory.run(max_projects=1, max_retries=0)

    assert result == [project]
    assert project.status == "blocked"
    assert "request preparation failed" in (project.last_error or "")
    assert next(
        step for step in project.plan.steps if step.stage.value == "execution"
    ).status == "failed"



@pytest.mark.asyncio
async def test_missing_autonomous_pipeline_does_not_mark_all_stages_completed() -> None:
    class InvalidAutonomousRunner:
        async def run(self, mission, plan, on_progress=None):
            return SimpleNamespace(pipeline=None, stages=[])

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=InvalidAutonomousRunner(),
    )
    project = factory.enqueue(
        CompanyMission(name="Invalid result", objective="Return no pipeline")
    )

    result = await factory.run(max_projects=1, max_retries=0)

    assert result == [project]
    assert project.status == "blocked"
    assert "no pipeline result" in (project.last_error or "")
    assert sum(step.status == "completed" for step in project.plan.steps) == 0
    assert any(step.status == "failed" for step in project.plan.steps)


@pytest.mark.asyncio
async def test_timed_out_mission_is_blocked_and_factory_continues() -> None:
    import asyncio

    class TimeoutThenSuccessRunner:
        def __init__(self):
            self.calls = 0

        async def run(self, mission, plan, on_progress=None):
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(10)
            return SimpleNamespace(pipeline=object(), stages=[])

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )
    runner = TimeoutThenSuccessRunner()
    factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        autonomous_runner=runner,
        execution_timeout_seconds=0.01,
    )
    timed_out = factory.enqueue(
        CompanyMission(name="Stalled mission", objective="Wait forever")
    )
    later = factory.enqueue(
        CompanyMission(name="Healthy mission", objective="Complete successfully")
    )

    results = await factory.run(max_projects=2, max_retries=0)

    assert timed_out.status == "blocked"
    assert "execution exceeded 0.01 seconds" in (timed_out.last_error or "")
    assert later.status == "completed"
    assert runner.calls == 2
    assert len(results) == 2



@pytest.mark.asyncio
async def test_factory_contains_unexpected_worker_error_and_continues_queue() -> None:
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(FakeRuntime()),
        AgentRegistry(),
    )

    class FailOnceStore:
        failed_mission_id = None
        should_fail = False

        def load_pending(self):
            return []

        def save(self, project):
            if self.should_fail and project.mission.id == self.failed_mission_id:
                self.should_fail = False
                raise RuntimeError("simulated persistence failure")

    store = FailOnceStore()
    factory = ProjectFactory(orchestrator, controller, pipeline, store=store)
    failed = factory.enqueue(
        CompanyMission(name="Worker error", objective="Fail safely outside execution")
    )
    later = factory.enqueue(
        CompanyMission(name="Later project", objective="Continue after worker error")
    )
    store.failed_mission_id = failed.mission.id
    store.should_fail = True

    results = await factory.run(max_projects=2, max_retries=0)

    assert failed.status == "blocked"
    assert "simulated persistence failure" in (failed.last_error or "")
    assert later.status == "completed"
    assert [item.mission.id for item in results] == [
        failed.mission.id,
        later.mission.id,
    ]
    assert factory._active_project is None



@pytest.mark.asyncio
async def test_executor_exception_marks_stage_failed_and_records_attempt() -> None:
    class ExplodingExecutor:
        async def execute(self, _context, _request):
            raise RuntimeError("model provider unavailable")

    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        ExplodingExecutor(),
        AgentRegistry(),
    )
    mission = CompanyMission(
        name="Provider outage",
        objective="Build a multi-feature application",
    )
    plan = build_mission_plan(mission)
    controller.start(mission)

    result = await pipeline.execute_next(mission, plan)

    first_step = plan.steps[0]
    assert result.success is False
    assert result.error == "RuntimeError: model provider unavailable"
    assert first_step.status == "failed"
    assert first_step.detail == result.error
    assert first_step.attempts == 1
    assert orchestrator.state.status.value != "running"
