from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class MissionStage(StrEnum):
    RESEARCH = "research"
    PRODUCT = "product"
    ARCHITECTURE = "architecture"
    TASKS = "tasks"
    AGENTS = "agents"
    EXECUTION = "execution"
    QA = "qa"
    SECURITY = "security"
    GITHUB = "github"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    LEARNING = "learning"


class PlannedStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    stage: MissionStage
    objective: str
    # Explicit prerequisites let planning/QA reason about ordering rather than
    # inferring a dependency graph from the list position alone.
    depends_on: list[str] = Field(default_factory=list)
    agent_role: str = "generalist"
    status: str = "planned"
    attempts: int = 0
    detail: str | None = None


class EngineeringTask(BaseModel):
    """A small, traceable unit of product work within a mission."""

    id: str
    title: str
    requirement: str
    workstream: str
    depends_on: list[str] = Field(default_factory=list)
    agent_role: str
    acceptance_check: str
    status: str = "planned"


class RequirementItem(BaseModel):
    """One traceable, reviewable requirement with a verifiable outcome."""

    id: str
    statement: str
    acceptance_check: str
    source: str = "objective"


class RequirementsContract(BaseModel):
    """Versioned, deterministic requirements contract created before engineering."""

    schema_version: int = 1
    mission_id: str
    mission_name: str
    objective: str
    status: str = "ready"
    functional_requirements: list[RequirementItem] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class MissionPlan(BaseModel):
    mission_id: str
    name: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    # Optional for backward compatibility with previously persisted mission plans.
    requirements_contract: RequirementsContract | None = None
    # Requirements remain attached to the durable plan so QA and review can
    # trace a finished product back to the user's original request.
    acceptance_criteria: list[str] = Field(default_factory=list)
    # Feature-level work items make large missions actionable without replacing
    # the existing lifecycle stages that coordinate the company.
    engineering_tasks: list[EngineeringTask] = Field(default_factory=list)
    # Server-generated provenance from the actual QA runner and security reviewer.
    qa_status: str | None = None
    qa_exit_code: int | None = None
    qa_duration_ms: int | None = None
    qa_command: list[str] = Field(default_factory=list)
    qa_evidence: str | None = None
    security_status: str | None = None
    security_summary: str | None = None
    security_evidence: str | None = None
    # Aggregated local-model usage from the generator, persisted for operations.
    generation_model_calls: int | None = None
    generation_duration_ms: int | None = None
    generation_prompt_tokens: int | None = None
    generation_output_tokens: int | None = None
    steps: list[PlannedStep]

    def engineering_task_order(self) -> list[EngineeringTask]:
        """Return a stable dependency-first order or reject an invalid task graph.

        Task state is durable in the plan, so callers can persist completed slices
        and resume by asking for the next ready tasks without regenerating finished work.
        """
        tasks = self.engineering_tasks
        by_id: dict[str, EngineeringTask] = {}
        for task in tasks:
            if not task.id or task.id in by_id:
                raise ValueError("engineering task IDs must be unique non-empty strings")
            by_id[task.id] = task

        for task in tasks:
            missing = [dependency for dependency in task.depends_on if dependency not in by_id]
            if missing:
                raise ValueError(
                    f"engineering task {task.id!r} has missing dependencies: "
                    + ", ".join(missing)
                )
            if task.id in task.depends_on:
                raise ValueError(f"engineering task {task.id!r} depends on itself")

        ordered: list[EngineeringTask] = []
        completed_ids: set[str] = set()
        remaining = list(tasks)
        while remaining:
            ready = [task for task in remaining if all(dep in completed_ids for dep in task.depends_on)]
            if not ready:
                raise ValueError("engineering task dependencies contain a cycle")
            for task in ready:
                ordered.append(task)
                completed_ids.add(task.id)
                remaining.remove(task)
        return ordered

    def ready_engineering_tasks(self) -> list[EngineeringTask]:
        """Return planned slices whose prerequisites are durably completed."""
        ordered = self.engineering_task_order()
        by_id = {task.id: task for task in self.engineering_tasks}
        return [
            task for task in ordered
            if task.status == "planned"
            and all(by_id[dep].status == "completed" for dep in task.depends_on)
        ]
