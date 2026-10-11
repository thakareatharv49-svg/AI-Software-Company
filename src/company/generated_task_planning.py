from __future__ import annotations

from collections import OrderedDict
from pathlib import PurePosixPath

from src.manager.models.contracts import TaskPlanItem


def _subsystem_for_path(path: str) -> str:
    """Map a generated file to a stable, human-readable work package."""
    parts = PurePosixPath(path).parts
    if not parts:
        return "application shell"
    first = parts[0].casefold()
    if first in {"tests", "test"} or PurePosixPath(path).name.casefold().startswith("test_"):
        return "quality and tests"
    if first == "src" and len(parts) > 2:
        return f"src/{parts[1]}"
    if first in {"frontend", "backend", "api", "database", "public", "assets", "docs", "scripts"}:
        return first
    if len(parts) > 1:
        return f"{parts[0]}/{parts[1]}"
    return "application shell"


def build_generated_task_plan(
    project_name: str,
    objective: str,
    files: dict[str, str],
) -> tuple[TaskPlanItem, ...]:
    """Create an ordered, auditable task plan from already-generated project files.

    Implementation work packages preserve first-seen file order. Test files are
    moved to the final QA work package so it depends on all implementation tasks.
    Dependencies use task indexes, as expected by MasterManager.create_plan().
    """
    if not files:
        raise ValueError("Cannot build a task plan for a project with no generated files")

    groups: OrderedDict[str, list[str]] = OrderedDict()
    for raw_path in files:
        path = PurePosixPath(raw_path.replace("\\", "/")).as_posix()
        if (
            path in {"", "."}
            or path.startswith("../")
            or PurePosixPath(path).is_absolute()
            or ":" in path
        ):
            raise ValueError(f"Unsafe generated file path in task plan: {raw_path!r}")
        groups.setdefault(_subsystem_for_path(path), []).append(path)

    implementation = [
        (name, paths) for name, paths in groups.items() if name != "quality and tests"
    ]
    quality = [
        (name, paths) for name, paths in groups.items() if name == "quality and tests"
    ]
    ordered = implementation + quality
    tasks: list[TaskPlanItem] = []
    for index, (subsystem, paths) in enumerate(ordered):
        is_quality = subsystem == "quality and tests"
        dependencies = (
            tuple(range(len(implementation)))
            if is_quality and implementation
            else ((index - 1,) if index > 0 else ())
        )
        tasks.append(
            TaskPlanItem(
                title=(
                    f"Validate {project_name} quality and tests"
                    if is_quality
                    else f"Integrate {project_name}: {subsystem}"
                ),
                description=(
                    f"Project objective: {objective}\n"
                    f"Work package: {subsystem}\n"
                    "Generated files:\n"
                    + "\n".join(f"- {path}" for path in paths)
                    + (
                        "\nRun and review the mission-specific behavioral tests; "
                        "do not weaken tests to make them pass."
                        if is_quality
                        else "\nReview these generated modules for integration with the project objective."
                    )
                ),
                priority="high" if is_quality else "medium",
                dependencies=dependencies,
            )
        )
    return tuple(tasks)
