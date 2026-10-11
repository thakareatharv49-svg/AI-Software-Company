from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath


def validate_generated_artifacts(files: Mapping[str, str]) -> list[str]:
    """Return release-blocking issues for unsafe or empty generated file sets."""
    issues: list[str] = []
    if not files:
        return ["Generated project contains no deliverable files."]

    seen: dict[str, str] = {}
    for path, content in files.items():
        if not isinstance(path, str) or not path.strip():
            issues.append("Generated artifact has an empty or invalid path.")
            continue
        if not isinstance(content, str):
            issues.append(f"Generated artifact '{path}' has non-text content.")
            continue

        normalized = path.replace("\\", "/").strip()
        pure_path = PurePosixPath(normalized)
        if (
            normalized.startswith("/")
            or pure_path.is_absolute()
            or any(part in {"", ".", ".."} for part in normalized.split("/"))
            or (len(normalized) >= 2 and normalized[1] == ":")
            or "\x00" in normalized
        ):
            issues.append(
                f"Generated artifact path '{path}' is not a safe relative path."
            )
            continue

        canonical = pure_path.as_posix().casefold()
        previous = seen.get(canonical)
        if previous is not None:
            issues.append(
                f"Generated artifacts '{previous}' and '{path}' collide on a "
                "case-insensitive filesystem."
            )
        else:
            seen[canonical] = path

        if not content.strip():
            issues.append(f"Generated artifact '{path}' is empty.")

    return issues
