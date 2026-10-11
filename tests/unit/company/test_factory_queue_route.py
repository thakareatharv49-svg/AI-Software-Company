from types import SimpleNamespace

import pytest

from src.company.control_center.routes import run_factory_queue
from src.company.mission_jobs import MissionJobStatus


class FakeControlCenter:
    def __init__(self, jobs):
        self.jobs = jobs
        self.enqueued = []
        self.run_args = None
        self.continuous_started = False

    def mission_jobs(self):
        return self.jobs

    def enqueue_factory_mission(self, mission_id):
        self.enqueued.append(mission_id)

    async def run_factory(self, **kwargs):
        self.run_args = kwargs

    async def start_continuous_factory(self, **kwargs):
        self.run_args = kwargs
        self.continuous_started = True


@pytest.mark.asyncio
async def test_run_factory_queue_enqueues_all_queued_missions_in_order():
    center = FakeControlCenter([
        SimpleNamespace(id="queued-1", status=MissionJobStatus.QUEUED),
        SimpleNamespace(id="completed", status=MissionJobStatus.COMPLETED),
        SimpleNamespace(id="queued-2", status=MissionJobStatus.QUEUED),
        SimpleNamespace(id="blocked", status=MissionJobStatus.BLOCKED),
    ])

    response = await run_factory_queue(max_retries=1, center=center)

    assert response == {"status": "continuous", "continuous": True, "queued_projects": 2}
    assert center.enqueued == []
    assert center.run_args == {"max_retries": 1}
    assert center.continuous_started is True


@pytest.mark.asyncio
async def test_run_factory_queue_returns_idle_when_no_queued_missions():
    center = FakeControlCenter([
        SimpleNamespace(id="completed", status=MissionJobStatus.COMPLETED),
        SimpleNamespace(id="blocked", status=MissionJobStatus.BLOCKED),
    ])

    response = await run_factory_queue(center=center)

    assert response == {"status": "continuous", "continuous": True, "queued_projects": 0}
    assert center.enqueued == []
    assert center.run_args == {"max_retries": 2}
    assert center.continuous_started is True
