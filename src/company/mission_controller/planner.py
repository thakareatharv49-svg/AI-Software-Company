import re

from src.company.mission_controller.models import MissionPlan, MissionStage, PlannedStep
from src.company.models.contracts import CompanyMission


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


_AGENT_ROLES = {
    MissionStage.RESEARCH: "research_analyst",
    MissionStage.PRODUCT: "product_manager",
    MissionStage.ARCHITECTURE: "software_architect",
    MissionStage.TASKS: "technical_planner",
    MissionStage.AGENTS: "agent_coordinator",
    MissionStage.EXECUTION: "software_engineer",
    MissionStage.QA: "test_engineer",
    MissionStage.SECURITY: "security_engineer",
    MissionStage.GITHUB: "release_engineer",
    MissionStage.DEPLOYMENT: "devops_engineer",
    MissionStage.MONITORING: "reliability_engineer",
    MissionStage.LEARNING: "evaluation_analyst",
}

# Dependencies are stage names, not random step IDs, so persisted plans remain
# understandable and can be compared across retries and process restarts.
_STAGE_DEPENDENCIES: dict[MissionStage, list[str]] = {
    MissionStage.RESEARCH: [],
    MissionStage.PRODUCT: [MissionStage.RESEARCH.value],
    MissionStage.ARCHITECTURE: [MissionStage.PRODUCT.value],
    MissionStage.TASKS: [MissionStage.ARCHITECTURE.value],
    MissionStage.AGENTS: [MissionStage.TASKS.value],
    MissionStage.EXECUTION: [MissionStage.AGENTS.value],
    # QA and security are independent checks on the same implementation.
    MissionStage.QA: [MissionStage.EXECUTION.value],
    MissionStage.SECURITY: [MissionStage.EXECUTION.value],
    MissionStage.GITHUB: [MissionStage.QA.value, MissionStage.SECURITY.value],
    MissionStage.DEPLOYMENT: [MissionStage.GITHUB.value],
    MissionStage.MONITORING: [MissionStage.DEPLOYMENT.value],
    MissionStage.LEARNING: [MissionStage.MONITORING.value],
}


def _acceptance_criteria(mission: CompanyMission) -> list[str]:
    """Extract stable, human-reviewable requirements from the mission request."""
    criteria: list[str] = []
    for chunk in re.split(r"(?<=[.!?])\\s+|\\n+|;\\s*", mission.objective.strip()):
        normalized = chunk.strip(" \\t\\r\\n-*•")
        if normalized and normalized not in criteria:
            criteria.append(normalized)
    for constraint in mission.constraints:
        normalized = constraint.strip()
        if normalized:
            criterion = f"Constraint: {normalized}"
            if criterion not in criteria:
                criteria.append(criterion)
    return criteria or [mission.objective.strip()]


def build_mission_plan(mission: CompanyMission) -> MissionPlan:
    """Build a durable engineering plan with requirements, roles, and dependencies."""
    return MissionPlan(
        mission_id=mission.id,
        name=mission.name,
        objective=mission.objective,
        constraints=list(mission.constraints),
        acceptance_criteria=_acceptance_criteria(mission),
        steps=[
            PlannedStep(
                stage=stage,
                objective=_STAGE_OBJECTIVES[stage],
                depends_on=list(_STAGE_DEPENDENCIES[stage]),
                agent_role=_AGENT_ROLES[stage],
            )
            for stage in MissionStage
        ],
    )
