from types import SimpleNamespace

from src.company.control_center.routes import factory_status
from src.company.mission_controller.planner import build_mission_plan
from src.company.mission_jobs import MissionJob, MissionJobStatus
from src.company.models.contracts import CompanyMission


def make_job(name: str, status: MissionJobStatus) -> MissionJob:
    mission = CompanyMission(name=name, objective=f"Build {name}")
    return MissionJob(
        id=mission.id,
        mission=mission,
        plan=build_mission_plan(mission),
        status=status,
        message=f"{status.value}: {name}",
    )


def test_factory_status_reports_durable_queue_and_live_order():
    in_memory = make_job("Prioritized", MissionJobStatus.QUEUED)
    durable_only = make_job("Waiting", MissionJobStatus.QUEUED)
    active = make_job("Active", MissionJobStatus.RUNNING)

    class Center:
        _factory = SimpleNamespace(
            queue=[
                SimpleNamespace(
                    mission=in_memory.mission,
                    status="queued",
                )
            ]
        )

        def mission_jobs(self):
            return [in_memory, durable_only, active]

        def factory_running(self):
            return True

        def continuous_factory_enabled(self):
            return True

    payload = factory_status(Center())

    assert payload["running"] is True
    assert payload["continuous"] is True
    assert payload["queued_projects"] == 2
    assert payload["queue_counts"]["queued"] == 2
    assert payload["queue_counts"]["running"] == 1
    assert [item["name"] for item in payload["queue_preview"]] == [
        "Prioritized",
        "Waiting",
    ]
    assert payload["queue_preview"][0]["position"] == 1
    assert payload["active_mission"]["name"] == "Active"


def test_factory_status_handles_empty_queue():
    class Center:
        _factory = SimpleNamespace(queue=[])

        def mission_jobs(self):
            return []

        def factory_running(self):
            return False

        def continuous_factory_enabled(self):
            return False

    payload = factory_status(Center())

    assert payload["queued_projects"] == 0
    assert payload["queue_preview"] == []
    assert payload["active_mission"] is None
    assert all(count == 0 for count in payload["queue_counts"].values())
