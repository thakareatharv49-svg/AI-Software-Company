"""Regression tests for recovery after continuous factory loop exceptions."""

from threading import Lock
from types import SimpleNamespace

import pytest

from src.company.control_center.service import CompanyControlCenter
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission


@pytest.mark.asyncio
async def test_continuous_runner_recovers_running_job_and_redacts_exception() -> None:
    mission = CompanyMission(name="Recover", objective="Recover an interrupted mission")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "running"
    plan.steps[0].detail = "generation interrupted"
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=MissionJobStatus.RUNNING,
        message="running",
        attempts=2,
    )

    class JobStore:
        def __init__(self):
            self.job = job

        def list_all(self):
            return [self.job]

        def save(self, updated):
            self.job = updated

    class Events:
        def __init__(self):
            self.published = []

        def publish(self, event):
            self.published.append(event)

    class Factory:
        def __init__(self, owner):
            self.owner = owner
            self.queue = []
            self.calls = 0

        def has_queued_mission(self, mission_id):
            return any(item.mission.id == mission_id for item in self.queue)

        def _save(self, _project):
            pass

        async def run(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("api_key=continuousSecret123456")
            self.owner._continuous_mode = False

    center = object.__new__(CompanyControlCenter)
    center._factory_paused = False
    center._continuous_mode = False
    center._factory_task = None
    center._lock = Lock()
    center._job_store = JobStore()
    center._jobs = {}
    center._missions = {}
    center._orchestrator = SimpleNamespace(events=Events())
    center._factory = Factory(center)

    await center.start_continuous_factory()
    await center._factory_task

    recovered = center._job_store.job
    assert recovered.status == MissionJobStatus.QUEUED
    assert recovered.plan.steps[0].status == "planned"
    assert len(center._factory.queue) == 1
    assert center._factory.queue[0].mission.id == mission.id
    assert center._factory.queue[0].attempts == 2
    assert center._factory.calls == 2
    loop_errors = [
        event for event in center._orchestrator.events.published
        if event.event_type == "FACTORY_CONTINUOUS_LOOP_ERROR"
    ]
    assert len(loop_errors) == 1
    assert "continuousSecret123456" not in loop_errors[0].message
