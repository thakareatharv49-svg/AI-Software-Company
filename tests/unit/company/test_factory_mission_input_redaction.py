from types import SimpleNamespace

from src.company.models.contracts import CompanyMission
from src.company.project_factory import ProjectFactory


def test_enqueue_redacts_secrets_from_mission_fields_before_persistence_and_planning():
    mission = CompanyMission(
        name="Budget app api_key=namesecret123456",
        objective="Build a budget app with password=objectivesecret123456",
        constraints=["Use database_url=constraintsecret123456 only in local config"],
    )
    saved_jobs = []
    saved_projects = []
    audit_entries = []

    class JobStore:
        def get(self, _mission_id):
            return None

        def save(self, job):
            saved_jobs.append(job)

    class Store:
        def save(self, project):
            saved_projects.append(project)

    class Audit:
        def append(self, entry):
            audit_entries.append(entry)

    factory = object.__new__(ProjectFactory)
    factory.job_store = JobStore()
    factory.store = Store()
    factory.audit_store = Audit()
    factory.queue = []
    factory._running = False
    factory.orchestrator = SimpleNamespace(
        events=SimpleNamespace(publish=lambda _event: None)
    )

    project = factory.enqueue(mission)
    persisted = saved_jobs[-1]

    for secret in ("namesecret123456", "objectivesecret123456", "constraintsecret123456"):
        assert secret not in persisted.mission.name
        assert secret not in persisted.mission.objective
        assert secret not in " ".join(persisted.mission.constraints)
        assert secret not in persisted.plan.objective
        assert secret not in " ".join(persisted.plan.constraints)
        assert secret not in " ".join(persisted.plan.acceptance_criteria)

    assert project.mission.name == persisted.mission.name
    assert "api_key=[REDACTED]" in persisted.mission.name
    assert "password=[REDACTED]" in persisted.mission.objective
    assert "database_url=[REDACTED]" in persisted.mission.constraints[0]
