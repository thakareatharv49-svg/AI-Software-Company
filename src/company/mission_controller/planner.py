from src.company.models.contracts import CompanyMission
from src.company.mission_controller.models import MissionPlan, MissionStage, PlannedStep


_STAGE_OBJECTIVES = {
    MissionStage.RESEARCH: (
        "Understand the problem, users, constraints, risks, and relevant evidence."
    ),
    MissionStage.PRODUCT: (
        "Define the product outcome, users, capabilities, and acceptance criteria."
    ),
    MissionStage.ARCHITECTURE: (
        "Design the system architecture, boundaries, interfaces, and data flow."
    ),
    MissionStage.TASKS: (
        "Break the architecture into ordered, independently executable engineering tasks."
    ),
    MissionStage.AGENTS: (
        "Map each task to the required autonomous agent capability and permissions."
    ),
    MissionStage.EXECUTION: (
        "Execute the planned engineering work and collect artifacts and results."
    ),
    MissionStage.QA: (
        "Validate behavior with automated tests, acceptance checks, and regression controls."
    ),
    MissionStage.SECURITY: (
        "Run security, permission, dependency, and data-handling checks."
    ),
    MissionStage.GITHUB: (
        "Prepare versioned source changes, commits, branches, and reviewable delivery."
    ),
    MissionStage.DEPLOYMENT: (
        "Build and release the validated product through the configured deployment path."
    ),
    MissionStage.MONITORING: (
        "Observe health, errors, performance, and operational signals after release."
    ),
    MissionStage.LEARNING: (
        "Capture outcomes and feedback so the company can improve the next mission."
    ),
}


def build_mission_plan(mission: CompanyMission) -> MissionPlan:
    return MissionPlan(
        mission_id=mission.id,
        name=mission.name,
        objective=mission.objective,
        constraints=list(mission.constraints),
        steps=[
            PlannedStep(stage=stage, objective=_STAGE_OBJECTIVES[stage])
            for stage in MissionStage
        ],
    )
