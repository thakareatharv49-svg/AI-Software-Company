import re

from src.company.mission_controller.models import (
    EngineeringTask,
    MissionPlan,
    MissionStage,
    PlannedStep,
)
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
    for chunk in re.split(r"(?<=[.!?])\s+|\n+|;\s*", mission.objective.strip()):
        normalized = chunk.strip(" \t\r\n-*•")
        if normalized and normalized not in criteria:
            criteria.append(normalized)
    for constraint in mission.constraints:
        normalized = constraint.strip()
        if normalized:
            criterion = f"Constraint: {normalized}"
            if criterion not in criteria:
                criteria.append(criterion)
    return criteria or [mission.objective.strip()]


def _build_engineering_tasks(criteria: list[str]) -> list[EngineeringTask]:
    """Turn each user requirement into design, implementation, and verification work."""
    tasks: list[EngineeringTask] = []
    for index, requirement in enumerate(criteria, start=1):
        prefix = f"req-{index:03d}"
        design_id = f"{prefix}-design"
        implementation_id = f"{prefix}-implementation"
        verification_id = f"{prefix}-verification"
        tasks.extend(
            [
                EngineeringTask(
                    id=design_id,
                    title=f"Design: {requirement}",
                    requirement=requirement,
                    workstream="design",
                    agent_role="software_architect",
                    acceptance_check="Interfaces, data needs, and edge cases are documented.",
                ),
                EngineeringTask(
                    id=implementation_id,
                    title=f"Implement: {requirement}",
                    requirement=requirement,
                    workstream="implementation",
                    depends_on=[design_id],
                    agent_role="software_engineer",
                    acceptance_check=f"Product behavior implements this requirement: {requirement}",
                ),
                EngineeringTask(
                    id=verification_id,
                    title=f"Verify: {requirement}",
                    requirement=requirement,
                    workstream="verification",
                    depends_on=[implementation_id],
                    agent_role="test_engineer",
                    acceptance_check=f"An automated test proves the requirement: {requirement}",
                ),
            ]
        )
    return tasks


def build_mission_plan(mission: CompanyMission) -> MissionPlan:
    """Build a durable engineering plan with requirements, roles, and dependencies."""
    criteria = _acceptance_criteria(mission)
    return MissionPlan(
        mission_id=mission.id,
        name=mission.name,
        objective=mission.objective,
        constraints=list(mission.constraints),
        acceptance_criteria=criteria,
        engineering_tasks=_build_engineering_tasks(criteria),
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

def validate_mission_plan(plan: MissionPlan) -> list[str]:
    """Return actionable structural errors in a plan's stage and task DAGs."""
    issues: list[str] = []
    stage_names = [step.stage.value for step in plan.steps]
    known_stages = set(stage_names)
    if len(stage_names) != len(known_stages):
        issues.append("Mission plan contains duplicate lifecycle stages.")
    for step in plan.steps:
        for dependency in step.depends_on:
            if dependency not in known_stages:
                issues.append(
                    f"Stage '{step.stage.value}' depends on unknown stage '{dependency}'."
                )
            elif dependency == step.stage.value:
                issues.append(f"Stage '{step.stage.value}' cannot depend on itself.")

    task_ids = [task.id for task in plan.engineering_tasks]
    known_tasks = set(task_ids)
    if len(task_ids) != len(known_tasks):
        issues.append("Engineering task IDs must be unique.")
    for task in plan.engineering_tasks:
        for dependency in task.depends_on:
            if dependency not in known_tasks:
                issues.append(
                    f"Task '{task.id}' depends on unknown task '{dependency}'."
                )
            elif dependency == task.id:
                issues.append(f"Task '{task.id}' cannot depend on itself.")

    def find_cycles(nodes: list[str], dependencies: dict[str, list[str]], label: str) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visited:
                return
            if node in visiting:
                issues.append(f"{label} dependency graph contains a cycle at '{node}'.")
                return
            visiting.add(node)
            for dependency in dependencies.get(node, []):
                if dependency in dependencies:
                    visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in nodes:
            visit(node)

    find_cycles(
        stage_names,
        {step.stage.value: step.depends_on for step in plan.steps},
        "Lifecycle stage",
    )
    find_cycles(
        task_ids,
        {task.id: task.depends_on for task in plan.engineering_tasks},
        "Engineering task",
    )
    if not plan.acceptance_criteria:
        issues.append("Mission plan must contain at least one acceptance criterion.")
    if not plan.engineering_tasks:
        issues.append("Mission plan must contain at least one engineering task.")
    return list(dict.fromkeys(issues))
