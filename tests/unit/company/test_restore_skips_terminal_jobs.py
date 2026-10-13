import pytest

from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission
from src.company.project_factory import ProjectFactory


@pytest.mark.parametrize(
    "terminal_status",
    [
        MissionJobStatus.COMPLETED,
        MissionJobStatus.FAILED,
        MissionJobStatus.BLOCKED,
        MissionJobStatus.CANCELLED,
    ],
)
def test_restore_does_not_resurrect_terminal_durable_jobs(terminal_status):
    mission = CompanyMission(
        name="Already finished",
        objective="Do not requeue a terminal mission after restart",
    )
    plan = build_mission_plan(mission)
    project_data = {
        "mission": mission,
        "plan": plan,
        "status": "cancelled" if terminal_status == MissionJobStatus.CANCELLED else "queued",
        "stages_executed": 0,
        "attempts": 1,
        "last_error": None,
        "retry_feedback": None,
    }
    job = MissionJob(
        id=mission.id,
        mission=mission,
        plan=plan,
        status=terminal_status,
        message="Terminal job state",
        attempts=1,
    )

    class ProjectStore:
        def __init__(self):
            self.deleted = []

        def load_pending(self):
            return [project_data]

        def delete_many(self, mission_ids):
            self.deleted.extend(mission_ids)

    class JobStore:
        def get(self, job_id):
            return job if job_id == mission.id else None

    store = ProjectStore()
    factory = object.__new__(ProjectFactory)
    factory.store = store
    factory.job_store = JobStore()
    factory.queue = []
    factory._active_project = None

    assert factory.restore() == 0
    assert factory.queue == []
    assert store.deleted == [mission.id]
