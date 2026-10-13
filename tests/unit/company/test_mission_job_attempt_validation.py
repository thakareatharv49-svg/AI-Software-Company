import pytest
from pydantic import ValidationError

from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission


def _job_data(attempts: int) -> dict:
    mission = CompanyMission(name="Attempts", objective="Validate attempt counter")
    return {
        "id": mission.id,
        "mission": mission,
        "plan": build_mission_plan(mission),
        "status": MissionJobStatus.QUEUED,
        "message": "queued",
        "attempts": attempts,
    }


def test_mission_job_accepts_zero_attempts():
    assert MissionJob(**_job_data(0)).attempts == 0


def test_mission_job_accepts_positive_attempts():
    assert MissionJob(**_job_data(3)).attempts == 3


def test_mission_job_rejects_negative_attempts():
    with pytest.raises(ValidationError, match="attempts"):
        MissionJob(**_job_data(-1))
