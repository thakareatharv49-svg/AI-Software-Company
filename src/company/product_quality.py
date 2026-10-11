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


def _test_function_has_assertion(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    assertion_helpers: set[str] | None = None,
) -> bool:
    """Return whether a test function makes or delegates an explicit assertion."""
    assertion_helpers = assertion_helpers or set()
    for node in ast.walk(function):
        if isinstance(node, ast.Assert):
            return True
        if not isinstance(node, ast.Call):
            continue
        called = node.func
        if isinstance(called, ast.Name) and called.id in assertion_helpers:
            return True
        # Support pytest exception assertions and unittest-style assertion methods.
        if isinstance(called, ast.Attribute):
            if called.attr == "raises" and isinstance(called.value, ast.Name):
                if called.value.id == "pytest":
                    return True
            if called.attr.startswith("assert") and isinstance(called.value, ast.Name):
                if called.value.id in {"self", "case", "test_case"}:
                    return True
    return False




def _is_file_presence_only_test(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Detect tests whose assertions only prove that generated files exist."""
    assertions = [
        node for node in ast.walk(function) if isinstance(node, ast.Assert)
    ]
    if not assertions:
        return False

    for assertion in assertions:
        calls = [
            node for node in ast.walk(assertion.test) if isinstance(node, ast.Call)
        ]
        if not calls or not any(
            isinstance(call.func, ast.Attribute)
            and call.func.attr in {"exists", "is_file", "is_dir"}
            for call in calls
        ):
            return False

    # Do not classify a test as a file-presence smoke check if it also calls
    # product code, computes a result, or exercises an exception path.
    for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
        if isinstance(call.func, ast.Name) and call.func.id == "Path":
            continue
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr in {"exists", "is_file", "is_dir"}
        ):
            continue
        return False
    return True

def find_weak_product_tests(files: Mapping[str, str]) -> list[str]:
    """Reject missing, tautological, no-op, and smoke-only generated test suites."""
    issues: list[str] = []
    discovered_test_modules = []
    for path in files:
        normalized = path.replace("\\", "/").casefold()
        basename = normalized.rsplit("/", 1)[-1]
        if (
            basename.startswith("test_")
            or basename.endswith("_test.py")
        ) and normalized.endswith(".py"):
            discovered_test_modules.append(path)
    if not discovered_test_modules:
        return [
            "Generated project contains no automated test files. Add mission-specific "
            "behavioral tests and at least one edge case before delivery."
        ]
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
        # Generated tests often keep reusable domain checks in helpers such as
        # assert_valid_note(note). Treat a call to a helper that itself asserts
        # as a real check, while still rejecting helpers that merely return values.
        assertion_helpers = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("assert_")
            and _test_function_has_assertion(node)
        } if tree is not None else set()
        no_op_tests = [
            function.name
            for function in test_functions
            if not _test_function_has_assertion(function, assertion_helpers)
        ]
        empty_test_module = (
            tree is not None
            and (name.startswith("test_") or name.endswith("_test.py"))
            and not test_functions
        )
        if empty_test_module:
            issues.append(
                f"Generated tests '{path}' contain no test functions. "
                "Add tests that verify mission-specific behavior and edge cases."
            )
        # Large-mission generation conventionally writes tests/test_project.py,
        # while older/single-pass generation used test_generated_project.py.
        # Apply the smoke-only rule to every generated test module so changing the
        # filename cannot bypass the behavioral-test requirement.
        generated_smoke_only = bool(test_names) and (
            test_names.issubset(_SMOKE_ONLY_TEST_NAMES)
            or (
                bool(test_functions)
                and all(
                    _is_file_presence_only_test(function)
                    for function in test_functions
                )
            )
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
        elif _has_literal_only_assertion(content):
            issues.append(
                f"Generated tests '{path}' contain a tautological assertion; "
                "test an actual product behavior and an edge case."
            )
    return issues
