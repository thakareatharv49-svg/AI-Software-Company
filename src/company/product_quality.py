"""Cross-product quality checks for generated source files."""

from __future__ import annotations

from collections.abc import Mapping
import ast
import re

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



# Objective keywords are mapped to common implementation/test vocabulary. This is a
# traceability guard, not a substitute for executing tests or reviewing behavior.
_MISSION_FEATURES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("create", (r"\\bcreate\\w*\\b", r"\\badd\\w*\\b", r"\\binsert\\w*\\b", r"\\bcrud\\b"), (r"\\bcreate\\w*\\b", r"\\badd\\w*\\b", r"\\binsert\\w*\\b", r"\\bcrud\\b")),
    ("edit/update", (r"\\bedit\\w*\\b", r"\\bupdate\\w*\\b", r"\\bmodify\\w*\\b", r"\\bcrud\\b"), (r"\\bedit\\w*\\b", r"\\bupdate\\w*\\b", r"\\bmodify\\w*\\b", r"\\bcrud\\b")),
    ("delete/remove", (r"\\bdelete\\w*\\b", r"\\bremove\\w*\\b", r"\\bdestroy\\w*\\b", r"\\bcrud\\b"), (r"\\bdelete\\w*\\b", r"\\bremove\\w*\\b", r"\\bdestroy\\w*\\b", r"\\bcrud\\b")),
    ("search", (r"\\bsearch\\w*\\b", r"\\bfind\\w*\\b", r"\\bquery\\w*\\b"), (r"\\bsearch\\w*\\b", r"\\bfind\\w*\\b", r"\\bquery\\w*\\b")),
    ("filter", (r"\\bfilter\\w*\\b",), (r"\\bfilter\\w*\\b")),
    ("pin/favorite", (r"\\bpin\\w*\\b", r"\\bfavorit\\w*\\b", r"\\bstar\\w*\\b"), (r"\\bpin\\w*\\b", r"\\bfavorit\\w*\\b", r"\\bstar\\w*\\b")),
    ("persistence", (r"\\bpersist\\w*\\b", r"\\blocalstorage\\b", r"\\bstorage\\b", r"\\bsave\\w*\\b", r"\\bload\\w*\\b", r"\\bdatabase\\b"), (r"\\bpersist\\w*\\b", r"\\blocalstorage\\b", r"\\bstorage\\b", r"\\bsave\\w*\\b", r"\\bload\\w*\\b", r"\\bdatabase\\b")),
    ("authentication", (r"\\bauthentication\\b", r"\\bauth\\b", r"\\blogin\\b", r"\\bsign.?in\\b"), (r"\\bauthentication\\b", r"\\bauth\\b", r"\\blogin\\b", r"\\bsign.?in\\b")),
    ("export", (r"\\bexport\\w*\\b", r"\\bdownload\\w*\\b"), (r"\\bexport\\w*\\b", r"\\bdownload\\w*\\b")),
    ("import", (r"\\bimport\\w*\\b", r"\\bupload\\w*\\b"), (r"\\bimport\\w*\\b", r"\\bupload\\w*\\b")),
    ("budget", (r"\\bbudget\\w*\\b",), (r"\\bbudget\\w*\\b")),
    ("validation", (r"\\bvalidat\\w*\\b", r"\\binvalid\\w*\\b", r"\\breject\\w*\\b"), (r"\\bvalidat\\w*\\b", r"\\binvalid\\w*\\b", r"\\breject\\w*\\b")),
)


def find_uncovered_mission_features(
    objective: str,
    files: Mapping[str, str],
) -> list[str]:
    """Find explicit mission features with no lexical trace in generated tests.

    The check intentionally limits itself to concrete workflow features. It does
    not claim that a keyword proves behavior; generated tests still run separately.
    """
    test_content = "\\n".join(
        content.casefold()
        for path, content in files.items()
        if (
            path.replace("\\\\", "/").casefold().startswith("tests/")
            or path.casefold().rsplit("/", 1)[-1].startswith("test_")
            or path.casefold().endswith("_test.py")
            or path.casefold().endswith((".test.js", ".spec.js", ".test.ts", ".spec.ts"))
        )
    )
    if not test_content:
        return []  # Missing-test policy reports this separately.

    objective_text = objective.casefold()
    issues: list[str] = []
    for feature, objective_patterns, test_patterns in _MISSION_FEATURES:
        if not any(re.search(pattern, objective_text) for pattern in objective_patterns):
            continue
        if not any(re.search(pattern, test_content) for pattern in test_patterns):
            issues.append(
                f"Mission explicitly requests '{feature}', but generated tests contain "
                "no corresponding feature reference. Add a behavioral test for this workflow."
            )
    return issues


def find_missing_product_tests(files: Mapping[str, str]) -> list[str]:
    """Require at least one conventional automated test module for broad projects."""
    test_modules = [
        path for path in files
        if (
            path.replace("\\", "/").casefold().rsplit("/", 1)[-1].startswith("test_")
            or path.replace("\\", "/").casefold().rsplit("/", 1)[-1].endswith("_test.py")
        ) and path.casefold().endswith(".py")
    ]
    if test_modules:
        return []
    return [
        "Generated project contains no automated test files. Add mission-specific "
        "behavioral tests and at least one edge case before delivery."
    ]



_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GitHub personal access token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("private key material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)


def find_exposed_secrets(files: Mapping[str, str]) -> list[str]:
    """Detect high-confidence credential material in shipped generated source."""
    issues: list[str] = []
    for path, content in files.items():
        normalized = path.replace("\\", "/").casefold()
        if normalized.startswith(("tests/", "docs/")):
            continue
        if normalized.endswith((".md", ".txt", ".rst", ".lock")):
            continue
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                issues.append(
                    f"Generated source '{path}' appears to contain {label}. "
                    "Remove the credential and load secrets from environment/configuration."
                )
    return issues
