from runtime.models.messages import ModelResponse
from src.agents.execution.executor import AgentExecutor
from src.agents.registry.registry import AgentRegistry
from src.company.mission_controller.controller import MissionController
from src.company.mission_controller.execution import MissionExecutionPipeline
from src.company.mission_jobs import MissionJobStatus, transition_job
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.persistence import (
    FactoryProjectRow,
    MissionJobRow,
    MissionJobStore,
    ProjectStore,
)
from src.company.project_factory import ProjectFactory
from src.db.base import Base


class RestartTestRuntime:
    async def generate(self, request):
        return ModelResponse(content="stage completed", model="fake", provider="fake")


def test_real_factory_restores_running_mission_once_after_store_reopen(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "factory-restart.sqlite"
    monkeypatch.setattr(
        "src.company.persistence.settings.database_url",
        f"sqlite:///{database_path.as_posix()}",
    )

    first_projects = ProjectStore()
    first_jobs = MissionJobStore()
    Base.metadata.create_all(
        first_projects._engine,
        tables=[FactoryProjectRow.__table__, MissionJobRow.__table__],
    )
    orchestrator = CompanyOrchestrator()
    controller = MissionController(orchestrator)
    pipeline = MissionExecutionPipeline(
        orchestrator,
        AgentExecutor(RestartTestRuntime()),
        AgentRegistry(),
    )
    first_factory = ProjectFactory(
        orchestrator,
        controller,
        pipeline,
        store=first_projects,
        job_store=first_jobs,
    )

    mission = CompanyMission(
        name="Process restart integration",
        objective="Recover durable mission state exactly once",
    )
    project = first_factory.enqueue(mission)
    project.plan.steps[0].status = "completed"
    project.plan.steps[0].detail = "checkpoint completed before restart"
    project.plan.steps[1].status = "running"
    project.plan.steps[1].detail = "interrupted stage"
    project.status = "running"
    project.attempts = 1
    first_projects.save(project)

    job = first_jobs.get(mission.id)
    assert job is not None
    first_jobs.save(
        transition_job(
            job.model_copy(update={"plan": project.plan, "attempts": 1}),
            MissionJobStatus.RUNNING,
            "worker interrupted by simulated process restart",
        )
    )
    first_projects.close()
    first_jobs.close()

    # Re-open the same on-disk database through fresh store objects, as a new
    # application process would do during startup.
    restored_projects = ProjectStore()
    restored_jobs = MissionJobStore()
    Base.metadata.create_all(
        restored_projects._engine,
        tables=[FactoryProjectRow.__table__, MissionJobRow.__table__],
    )
    recovered_jobs = restored_jobs.recover_running()
    assert len(recovered_jobs) == 1
    assert recovered_jobs[0].status == MissionJobStatus.QUEUED

    restored_orchestrator = CompanyOrchestrator()
    restored_controller = MissionController(restored_orchestrator)
    restored_pipeline = MissionExecutionPipeline(
        restored_orchestrator,
        AgentExecutor(RestartTestRuntime()),
        AgentRegistry(),
    )
    restored_factory = ProjectFactory(
        restored_orchestrator,
        restored_controller,
        restored_pipeline,
        store=restored_projects,
        job_store=restored_jobs,
    )

    try:
        assert restored_factory.restore() == 1
        assert len(restored_factory.queue) == 1
        recovered = restored_factory.queue[0]
        assert recovered.mission.id == mission.id
        assert recovered.status == "queued"
        assert recovered.plan.steps[0].status == "completed"
        assert recovered.plan.steps[0].detail == "checkpoint completed before restart"
        assert recovered.plan.steps[1].status == "planned"
        assert recovered.plan.steps[1].detail is None
        durable = restored_jobs.get(mission.id)
        assert durable is not None
        assert durable.status == MissionJobStatus.QUEUED
        assert durable.attempts == 1
    finally:
        restored_projects.close()
        restored_jobs.close()
