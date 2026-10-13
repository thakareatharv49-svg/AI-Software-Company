import pytest

from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus, transition_job
from src.company.models.contracts import CompanyMission


def make_job(status: MissionJobStatus = MissionJobStatus.QUEUED) -> MissionJob:
    mission = CompanyMission(name="Lifecycle", objective="Track lifecycle")
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=status,
        message="created",
    )


def test_job_lifecycle_allows_queue_run_complete() -> None:
    job = make_job()
    job = transition_job(job, MissionJobStatus.RUNNING, "started")
    job = transition_job(job, MissionJobStatus.COMPLETED, "done")

    assert job.status == MissionJobStatus.COMPLETED
    assert job.message == "done"


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (MissionJobStatus.COMPLETED, MissionJobStatus.RUNNING),
        (MissionJobStatus.CANCELLED, MissionJobStatus.QUEUED),
        (MissionJobStatus.QUEUED, MissionJobStatus.COMPLETED),
    ],
)
def test_job_lifecycle_rejects_invalid_transitions(
    source: MissionJobStatus,
    target: MissionJobStatus,
) -> None:
    with pytest.raises(ValueError, match="Invalid mission transition"):
        transition_job(make_job(source), target, "invalid")


def test_failed_job_can_be_requeued() -> None:
    job = transition_job(make_job(), MissionJobStatus.RUNNING, "started")
    job = transition_job(job, MissionJobStatus.FAILED, "temporary failure")
    job = transition_job(job, MissionJobStatus.QUEUED, "retry")

    assert job.status == MissionJobStatus.QUEUED


def test_running_job_recovers_to_queued() -> None:
    from src.company.mission_jobs import recover_running_job
    recovered = recover_running_job(make_job(MissionJobStatus.RUNNING))
    assert recovered.status == MissionJobStatus.QUEUED
    assert "restart" in recovered.message.lower()


def test_recovery_does_not_change_non_running_job() -> None:
    from src.company.mission_jobs import recover_running_job
    job = make_job(MissionJobStatus.BLOCKED)
    assert recover_running_job(job) == job


def test_audit_entry_defaults_are_valid() -> None:
    from src.company.audit import MissionAuditEntry

    entry = MissionAuditEntry(
        id="audit-1",
        mission_id="mission-1",
        event_type="MISSION_CREATED",
        message="created",
    )

    assert entry.status is None
    assert entry.metadata == {}



def test_mission_job_keeps_workspace_ownership_through_transitions() -> None:
    job = make_job()
    owned = job.model_copy(update={"workspace_id": "customer-workspace-123"})
    running = transition_job(owned, MissionJobStatus.RUNNING, "started")

    assert running.workspace_id == "customer-workspace-123"



def test_running_stage_recovers_to_planned_and_completed_stages_are_preserved() -> None:
    from src.company.mission_jobs import recover_running_job

    job = make_job(MissionJobStatus.RUNNING)
    job.plan.steps[0].status = "completed"
    job.plan.steps[0].detail = "finished before restart"
    job.plan.steps[1].status = "running"
    job.plan.steps[1].detail = "interrupted during execution"

    recovered = recover_running_job(job)

    assert recovered.status == MissionJobStatus.QUEUED
    assert recovered.plan.steps[0].status == "completed"
    assert recovered.plan.steps[0].detail == "finished before restart"
    assert recovered.plan.steps[1].status == "planned"
    assert recovered.plan.steps[1].detail is None
    assert "interrupted stage" in recovered.message.lower()


def test_recover_running_plan_only_resets_in_flight_steps() -> None:
    from src.company.mission_jobs import recover_running_plan

    plan = build_mission_plan(CompanyMission(name="Resume", objective="Recover safely"))
    plan.steps[0].status = "completed"
    plan.steps[1].status = "failed"
    plan.steps[1].detail = "prior failure"
    plan.steps[2].status = "running"

    recovered = recover_running_plan(plan)

    assert recovered.steps[0].status == "completed"
    assert recovered.steps[1].status == "failed"
    assert recovered.steps[1].detail == "prior failure"
    assert recovered.steps[2].status == "planned"
    assert recovered.steps[2].detail is None



def test_mission_plan_captures_acceptance_criteria_and_specialist_dependencies() -> None:
    mission = CompanyMission(
        name="Notes",
        objective="Build a notes app. Support search; export notes.",
        constraints=["Work offline"],
    )
    plan = build_mission_plan(mission)
    steps = {step.stage.value: step for step in plan.steps}

    assert plan.acceptance_criteria == [
        "Build a notes app.",
        "Support search",
        "export notes.",
        "Constraint: Work offline",
    ]
    assert steps["research"].depends_on == []
    assert steps["architecture"].depends_on == ["product"]
    assert steps["qa"].depends_on == ["execution"]
    assert steps["security"].depends_on == ["execution"]
    assert steps["github"].depends_on == ["qa", "security"]
    assert steps["execution"].agent_role == "software_engineer"
    assert steps["qa"].agent_role == "test_engineer"



def test_large_mission_breaks_each_acceptance_criterion_into_traceable_tasks() -> None:
    mission = CompanyMission(
        name="Project Hub",
        objective="Create projects. Assign tasks; track progress.",
        constraints=["Keep user data private"],
    )
    plan = build_mission_plan(mission)

    assert len(plan.acceptance_criteria) == 4
    assert len(plan.engineering_tasks) == len(plan.acceptance_criteria) * 3
    tasks = {task.id: task for task in plan.engineering_tasks}

    for index, requirement in enumerate(plan.acceptance_criteria, start=1):
        prefix = f"req-{index:03d}"
        design = tasks[f"{prefix}-design"]
        implementation = tasks[f"{prefix}-implementation"]
        verification = tasks[f"{prefix}-verification"]

        assert design.requirement == requirement
        assert design.depends_on == []
        assert implementation.depends_on == [design.id]
        assert verification.depends_on == [implementation.id]
        assert verification.agent_role == "test_engineer"
        assert requirement in verification.acceptance_check
        assert {design.status, implementation.status, verification.status} == {"planned"}


def test_mission_job_redacts_and_bounds_messages_on_construction() -> None:
    job = make_job()
    unsafe = job.model_copy(update={"message": "api_key=storedSecret123456"})
    # Re-validation is used for durable snapshots loaded from older versions.
    restored = MissionJob.model_validate(unsafe.model_dump())

    assert "storedSecret123456" not in restored.message
    assert "api_key=[REDACTED]" in restored.message

    bounded = MissionJob.model_validate(
        {**job.model_dump(), "message": "diagnostic " * 1000}
    )
    assert len(bounded.message) == 4000


def test_mission_job_transition_redacts_untrusted_diagnostics() -> None:
    job = transition_job(
        make_job(),
        MissionJobStatus.RUNNING,
        "Worker failed: password=jobSecret123456",
    )

    assert "jobSecret123456" not in job.message
    assert "password=[REDACTED]" in job.message
