from types import SimpleNamespace

import pytest

from src.company.control_center.service import CompanyControlCenter, MissionSubmission
from src.company.mission_jobs import MissionJobStatus
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.config.settings import settings


class ExistingJobs:
    def list_all(self):
        return [SimpleNamespace(status=MissionJobStatus.QUEUED)]


def test_submit_mission_rejects_work_when_durable_queue_is_at_capacity(monkeypatch):
    center = CompanyControlCenter(CompanyOrchestrator())
    center._job_store = ExistingJobs()
    monkeypatch.setattr(settings, "factory_max_queued_missions", 1)

    with pytest.raises(RuntimeError, match="Mission queue is full"):
        center.submit_mission(
            MissionSubmission(name="Queue overflow", objective="Do not enqueue more work")
        )
