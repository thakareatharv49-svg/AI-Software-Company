from __future__ import annotations

from collections.abc import Mapping, Sequence


def order_manifest_paths(
    paths: Sequence[str],
    dependencies: Mapping[str, Sequence[str]],
) -> list[str]:
    """Return a stable topological order, rejecting invalid dependency graphs.

    The input order is the tie-breaker so callers can preserve their preferred
    ordering (for example, browser entry points before implementation modules).
    """
    ordered_paths = list(paths)
    if len(set(ordered_paths)) != len(ordered_paths):
        raise ValueError("Project manifest contains duplicate paths")

    known = set(ordered_paths)
    normalized: dict[str, tuple[str, ...]] = {}
    for path in ordered_paths:
        required = tuple(dependencies.get(path, ()))
        if path in required:
            raise ValueError(f"Project file {path!r} cannot depend on itself")
        if len(set(required)) != len(required):
            raise ValueError(f"Project file {path!r} repeats a dependency")
        missing = [item for item in required if item not in known]
        if missing:
            raise ValueError(
                f"Project file {path!r} depends on unknown path(s): {', '.join(missing)}"
            )
        normalized[path] = required

    result: list[str] = []
    completed: set[str] = set()
    remaining = set(ordered_paths)
    while remaining:
        ready = [
            path for path in ordered_paths
            if path in remaining and all(dep in completed for dep in normalized[path])
        ]
        if not ready:
            cycle_members = [path for path in ordered_paths if path in remaining]
            raise ValueError(
                "Project manifest contains a dependency cycle involving: "
                + ", ".join(cycle_members)
            )
        for path in ready:
            result.append(path)
            completed.add(path)
            remaining.remove(path)
    return result
