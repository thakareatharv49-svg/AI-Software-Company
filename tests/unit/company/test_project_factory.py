from pathlib import Path

import pytest

from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
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
async def test_factory_stops_after_blocked_project() -> None:
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
    queued = factory.enqueue(CompanyMission(name="Later", objective="Should remain queued"))

    results = await factory.run(max_projects=2, max_retries=0)

    assert project.status == "blocked"
    assert queued.status == "queued"
    assert len(results) == 1
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
            files={},
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
    assert project.stages_executed == 12
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
