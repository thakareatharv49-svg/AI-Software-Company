"""Cross-product quality checks for generated source files."""

from __future__ import annotations

from collections.abc import Mapping

# These phrases are strong signals that the model returned an unfinished product.
# Deliberately avoid generic words such as "placeholder" or "todo", which can be
# legitimate UI labels and product names.
_UNFINISHED_MARKERS = (
    "coming soon",
    "lorem ipsum",
    "todo: implement",
    "not implemented yet",
    "feature not available yet",
    "replace this with your implementation",
    "insert code here",
    "your content here",
    "sample text goes here",
    "functionality will be added later",
)


def find_unfinished_product_content(files: Mapping[str, str]) -> list[str]:
    """Return actionable issues when generated product source contains obvious placeholders.

    Test fixtures and documentation are excluded: this gate targets shipped source
    rather than examples that may intentionally discuss unfinished content.
    """
    issues: list[str] = []
    for path, content in files.items():
        normalized = path.replace("\\", "/").casefold()
        if normalized.startswith(("tests/", "docs/")):
            continue
        if normalized.endswith((".md", ".txt", ".rst")):
            continue
        lowered = content.casefold()
        for marker in _UNFINISHED_MARKERS:
            if marker in lowered:
                issues.append(
                    f"Generated source '{path}' contains unfinished placeholder text "
                    f"({marker!r}); implement the feature instead of shipping a placeholder."
                )
                break
    return issues
