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


def test_mission_job_preserves_zero_attempts():
    assert MissionJob(**_job_data(0)).attempts == 0


def test_mission_job_preserves_positive_attempts():
    assert MissionJob(**_job_data(3)).attempts == 3


def test_mission_job_normalizes_negative_legacy_attempts():
    assert MissionJob(**_job_data(-1)).attempts == 0


def test_mission_job_normalizes_malformed_attempts():
    assert MissionJob(**_job_data("not-an-integer")).attempts == 0
