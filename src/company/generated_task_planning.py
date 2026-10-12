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
    filename = PurePosixPath(path).name.casefold()
    if first in {"tests", "test"} or filename.startswith("test_"):
        return "quality and tests"
    # Generators frequently emit small Python services at the repository root
    # instead of placing them under src/. Keep those services distinct from the
    # browser shell so the factory creates an integration work package for them.
    if len(parts) == 1 and filename in {
        "api.py", "server.py", "database.py", "db.py", "models.py",
        "routes.py", "schemas.py", "services.py",
    }:
        return "backend"
    # Flat browser assets need their own work package, separate from root-level Python services.
    if len(parts) == 1 and PurePosixPath(filename).suffix in {".html", ".css", ".js"}:
        return "frontend"
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
    """Build a dependency graph from generated files.

    Independent implementation work packages have no artificial ordering
    dependency, allowing a concurrency-aware scheduler to run them in parallel.
    The final QA work package depends on every implementation package.
    Dependencies use task indexes, as expected by MasterManager.create_plan().
    """
    if not files:
        raise ValueError("Cannot build a task plan for a project with no generated files")

    groups: OrderedDict[str, list[str]] = OrderedDict()
    seen_paths: set[str] = set()
    for raw_path in files:
        path = PurePosixPath(raw_path.replace("\\", "/")).as_posix()
        parsed_path = PurePosixPath(path)
        if (
            path in {"", "."}
            or parsed_path.is_absolute()
            or ":" in path
            or ".." in parsed_path.parts
        ):
            raise ValueError(f"Unsafe generated file path in task plan: {raw_path!r}")
        # Backslash and slash spellings must not create duplicate output paths.
        normalized_path = path.casefold()
        if normalized_path in seen_paths:
            raise ValueError(
                f"Duplicate generated file path after normalization: {raw_path!r}"
            )
        seen_paths.add(normalized_path)
        groups.setdefault(_subsystem_for_path(path), []).append(path)

    if not any(content.strip() for content in files.values()):
        raise ValueError("Cannot build a task plan from entirely empty generated files")

    implementation = [
        (name, paths) for name, paths in groups.items() if name != "quality and tests"
    ]
    if not implementation:
        raise ValueError(
            "Cannot build a product task plan without generated implementation files"
        )
    quality = [
        (name, paths) for name, paths in groups.items() if name == "quality and tests"
    ]
    ordered = implementation + quality
    tasks: list[TaskPlanItem] = []
    implementation_count = len(implementation)
    for subsystem, paths in ordered:
        is_quality = subsystem == "quality and tests"
        dependencies = tuple(range(implementation_count)) if is_quality else ()
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
