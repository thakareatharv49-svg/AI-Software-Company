"""Cross-product quality checks for generated source files."""

from __future__ import annotations

from collections.abc import Mapping
import ast

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

# These are deterministic signs that generated tests do not test product behavior.
# Keep the detector deliberately narrow to avoid rejecting legitimate test suites.
_SMOKE_ONLY_TEST_NAMES = {
    "test_generated_python_compiles",
    "test_browser_entrypoint_and_local_assets_exist",
    "test_generated_source_files_exist",
}

_WEAK_TEST_ASSERTIONS = (
    r"assert\s+True\b",
    r"assert\s+1\s*==\s*1\b",
    r"assert\s+0\s*==\s*0\b",
)


def _has_literal_only_assertion(content: str) -> bool:
    """Detect asserts that compare constants instead of exercising product behavior."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # Syntax validity is checked by the normal generated-project test runner.
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        expression = node.test
        if isinstance(expression, ast.Constant):
            return True
        if isinstance(expression, ast.Compare):
            operands = [expression.left, *expression.comparators]
            if all(isinstance(operand, ast.Constant) for operand in operands):
                return True
    return False


def _test_function_has_assertion(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a test function makes an explicit, observable assertion."""
    for node in ast.walk(function):
        if isinstance(node, ast.Assert):
            return True
        if not isinstance(node, ast.Call):
            continue
        called = node.func
        # Support pytest exception assertions and unittest-style assertion methods.
        if isinstance(called, ast.Attribute):
            if called.attr == "raises" and isinstance(called.value, ast.Name):
                if called.value.id == "pytest":
                    return True
            if called.attr.startswith("assert") and isinstance(called.value, ast.Name):
                if called.value.id in {"self", "case", "test_case"}:
                    return True
    return False


def find_weak_product_tests(files: Mapping[str, str]) -> list[str]:
    """Reject tautologies, no-op test functions, and smoke-only generated suites."""
    import re

    issues: list[str] = []
    for path, content in files.items():
        normalized = path.replace("\\", "/").casefold()
        name = normalized.rsplit("/", 1)[-1]
        in_tests = (
            normalized.startswith("tests/")
            or name.startswith("test_")
            or name.endswith("_test.py")
        )
        if not in_tests or not name.endswith(".py"):
            continue
        has_regex_tautology = any(
            re.search(marker, content, flags=re.IGNORECASE)
            for marker in _WEAK_TEST_ASSERTIONS
        )
        try:
            tree = ast.parse(content)
        except SyntaxError:
            tree = None
        test_names = (
            {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            }
            if tree is not None
            else set()
        )
        test_functions = (
            [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            ]
            if tree is not None
            else []
        )
        no_op_tests = [
            function.name
            for function in test_functions
            if not _test_function_has_assertion(function)
        ]
        generated_smoke_only = (
            name == "test_generated_project.py"
            and bool(test_names)
            and test_names.issubset(_SMOKE_ONLY_TEST_NAMES)
        )
        if no_op_tests:
            issues.append(
                f"Generated tests '{path}' contain test function(s) without an "
                f"explicit assertion or exception check: {', '.join(no_op_tests)}. "
                "Assert the expected product behavior or expected failure."
            )
        if generated_smoke_only:
            issues.append(
                f"Generated tests '{path}' contain only generated smoke checks; "
                "add mission-specific behavioral tests and at least one edge case."
            )
        elif has_regex_tautology or _has_literal_only_assertion(content):
            issues.append(
                f"Generated tests '{path}' contain a tautological assertion; "
                "test an actual product behavior and an edge case."
            )
    return issues
