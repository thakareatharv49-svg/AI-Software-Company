from src.company.mission_controller.planner import build_mission_plan
from src.company.models.contracts import CompanyMission
from src.company.orchestration.orchestrator import CompanyOrchestrator
from src.company.project_factory import FactoryProject, ProjectFactory


class CaptureAuditStore:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        self.entries.append(entry)


def make_factory(audit_store):
    orchestrator = CompanyOrchestrator()
    return ProjectFactory(
        orchestrator=orchestrator,
        controller=None,
        pipeline=None,
        audit_store=audit_store,
    )


def test_progress_persistence_appends_stage_timeline_snapshot():
    audit = CaptureAuditStore()
    factory = make_factory(audit)
    mission = CompanyMission(name="Timeline", objective="Track execution stages")
    plan = build_mission_plan(mission)
    plan.steps[0].status = "completed"
    plan.steps[0].detail = "Research complete"
    plan.steps[1].status = "running"
    plan.steps[1].attempts = 2
    project = FactoryProject(mission=mission, plan=plan, status="running", attempts=1)

    factory._persist_plan_progress(project)

    assert len(audit.entries) == 1
    entry = audit.entries[0]
    assert entry.event_type == "MISSION_PROGRESS_SNAPSHOT"
    assert entry.metadata["attempt"] == 1
    timeline = entry.metadata["stage_timeline"]
    assert timeline[0]["stage"] == plan.steps[0].stage.value
    assert timeline[0]["status"] == "completed"
    assert timeline[0]["detail"] == "Research complete"
    assert timeline[1]["status"] == "running"
    assert timeline[1]["attempts"] == 2


def test_progress_timeline_redacts_sensitive_stage_details():
    audit = CaptureAuditStore()
    factory = make_factory(audit)
    mission = CompanyMission(name="Safe timeline", objective="Redact timeline details")
    plan = build_mission_plan(mission)
    plan.steps[0].detail = "api_key=timelineSecret123456"
    project = FactoryProject(mission=mission, plan=plan, status="running")

    factory._persist_plan_progress(project)

    entry = audit.entries[0]
    detail = entry.metadata["stage_timeline"][0]["detail"]
    assert "timelineSecret123456" not in detail
    assert "api_key=[REDACTED]" in detail
