from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath
import re
from urllib.parse import unquote, urlsplit


_HTML_REFERENCE = re.compile(
    r"""\b(?:src|href)\s*=\s*(['"])(.*?)\1""",
    re.IGNORECASE | re.DOTALL,
)
_CSS_URL = re.compile(
    r"""url\(\s*(['"]?)(.*?)\1\s*\)""",
    re.IGNORECASE | re.DOTALL,
)


def _local_asset_path(reference: str, owner_path: str) -> str | None:
    """Resolve a file-like local reference; ignore URLs and in-page routes."""
    value = reference.strip()
    if not value or value.startswith("#"):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path).replace("\\", "/")
    if not path or path.endswith("/"):
        return None
    # Extensionless hrefs are commonly client-side routes, not static files.
    if not PurePosixPath(path).suffix:
        return None
    if path.startswith("/"):
        resolved = path.lstrip("/")
    else:
        resolved = str(PurePosixPath(owner_path).parent / path)
    normalized = PurePosixPath(resolved).as_posix()
    if normalized.startswith("../") or normalized == "..":
        return None
    return normalized.casefold()


def validate_generated_artifacts(files: Mapping[str, str]) -> list[str]:
    """Return release-blocking issues for unsafe or incomplete generated files."""
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

    # Resolve references only after canonical paths have been collected so
    # ordering of the generated-file dictionary cannot affect validation.
    available = set(seen)
    for path, content in files.items():
        if not isinstance(path, str) or not isinstance(content, str):
            continue
        suffix = PurePosixPath(path.replace("\\", "/")).suffix.casefold()
        references: list[str] = []
        if suffix in {".html", ".htm"}:
            references.extend(match.group(2) for match in _HTML_REFERENCE.finditer(content))
        elif suffix == ".css":
            references.extend(match.group(2) for match in _CSS_URL.finditer(content))

        for reference in references:
            target = _local_asset_path(reference, path.replace("\\", "/"))
            if target is not None and target not in available:
                issues.append(
                    f"Generated artifact '{path}' references missing local asset "
                    f"'{reference.strip()}'."
                )

    return issues
