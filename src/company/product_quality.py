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
_MISSION_FEATURES: tuple[tuple[str, set[str], set[str]], ...] = (
    ("create", {"create", "add", "insert", "crud"}, {"create", "add", "insert", "crud"}),
    ("edit/update", {"edit", "update", "modify", "crud"}, {"edit", "update", "modify", "crud"}),
    ("delete/remove", {"delete", "remove", "destroy", "crud"}, {"delete", "remove", "destroy", "crud"}),
    ("search", {"search", "find", "query"}, {"search", "find", "query"}),
    ("filter", {"filter"}, {"filter"}),
    ("pin/favorite", {"pin", "favorite", "favourite", "star"}, {"pin", "favorite", "favourite", "star"}),
    ("authentication", {"authentication", "auth", "login", "signin"}, {"authentication", "auth", "login", "signin"}),
    ("export", {"export", "download"}, {"export", "download"}),
    ("import", {"import", "upload"}, {"import", "upload"}),
    ("budget", {"budget"}, {"budget"}),
    ("persistence", {"persistent", "persistence", "persist", "storage", "localstorage"}, {"persistent", "persistence", "persist", "storage", "localstorage"}),
    ("validation", {"validation", "validate", "validated"}, {"validation", "validate", "validated"}),
    ("sorting", {"sort", "sorting", "order"}, {"sort", "sorting", "order"}),
    ("undo/redo", {"undo", "redo"}, {"undo", "redo"}),
)


def find_weak_javascript_tests(files: Mapping[str, str]) -> list[str]:
    """Reject obvious empty or tautological tests in generated JavaScript/TypeScript suites.

    This is intentionally a narrow guard: it catches common model-generated
    no-op patterns without attempting to parse JavaScript with regular expressions.
    Actual test execution remains the authoritative runtime check.
    """
    issues: list[str] = []
    empty_test = re.compile(
        r"""\b(?:test|it)\s*\(\s*(['"`])[^'"\`]*\1\s*,\s*"""
        r"""(?:async\s*)?\(\s*\)\s*=>\s*\{\s*\}\s*\)""",
        re.IGNORECASE | re.DOTALL,
    )
    empty_function_test = re.compile(
        r"""\b(?:test|it)\s*\(\s*(['\"])[^'\"]*\1\s*,\s*"""
        r"""(?:async\s+)?function\s*\(\s*\)\s*\{\s*\}\s*\)""",
        re.IGNORECASE | re.DOTALL,
    )
    assertion_free_callback = re.compile(
        r"""\b(?:test|it)\s*\(\s*(['"`])[^'"`]*\1\s*,\s*"""
        r"""(?:async\s*)?\(\s*\)\s*=>\s*\{\s*"""
        r"""(?!(?:expect|assert|should|verify|check)\b)"""
        r"""(?:await\s+)?[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*"""
        r"""\s*\([^{};]*\)\s*;?\s*\}\s*\)""",
        re.IGNORECASE | re.DOTALL,
    )
    tautologies = (
        re.compile(r"""\bexpect\(\s*(true|false|null|[-+]?\d+(?:\.\d+)?|(['"]).*?\2)\s*\)\s*\.\s*toBe\(\s*\1\s*\)""", re.DOTALL),
        re.compile(r"""\bassert\.(?:equal|strictEqual|deepEqual)\(\s*(true|false|null|[-+]?\d+(?:\.\d+)?|(['"]).*?\2)\s*,\s*\1\s*\)""", re.DOTALL),
    )
    javascript_extensions = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
    javascript_test_suffixes = tuple(
        f"{kind}{extension}"
        for extension in javascript_extensions
        for kind in (".test", ".spec", "_test")
    )
    for path, content in files.items():
        normalized = path.replace("\\", "/").casefold()
        filename = normalized.rsplit("/", 1)[-1]
        is_test = (
            normalized.startswith(("tests/", "__tests__/"))
            or "/tests/" in normalized
            or "/__tests__/" in normalized
            or filename.startswith("test_")
            or filename.endswith(javascript_test_suffixes)
        )
        if not is_test or not filename.endswith(javascript_extensions):
            continue
        if empty_test.search(content) or empty_function_test.search(content):
            issues.append(
                f"Generated JavaScript test '{path}' contains an empty test body. "
                "Exercise product behavior and assert the expected result."
            )
        elif assertion_free_callback.search(content):
            issues.append(
                f"Generated JavaScript test '{path}' calls code without an explicit assertion. "
                "Assert the returned state, rendered output, or expected failure."
            )
        if any(pattern.search(content) for pattern in tautologies):
            issues.append(
                f"Generated JavaScript test '{path}' contains a tautological assertion. "
                "Assert a result derived from the product behavior instead."
            )
    return issues


def find_uncovered_mission_features(
    objective: str,
    files: Mapping[str, str],
) -> list[str]:
    """Require each requested workflow to appear in an actual test case name/title.

    This is a lightweight traceability guard, not proof that a test behaves
    correctly. The separate weak-test checks and test runner validate test bodies.
    Restricting evidence to test names/titles avoids counting comments, imports,
    fixtures, or unrelated helper functions as coverage for a mission feature.
    """
    def words(text: str) -> set[str]:
        return set(re.findall(r"[a-z]+", text.casefold()))

    objective_words = words(objective)
    javascript_test_suffixes = (
        "_test.js", "_test.jsx", "_test.mjs", "_test.cjs",
        "_test.ts", "_test.tsx", "_test.mts", "_test.cts",
        ".test.js", ".test.jsx", ".test.mjs", ".test.cjs",
        ".test.ts", ".test.tsx", ".test.mts", ".test.cts",
        ".spec.js", ".spec.jsx", ".spec.mjs", ".spec.cjs",
        ".spec.ts", ".spec.tsx", ".spec.mts", ".spec.cts",
    )

    def is_test_path(path: str) -> bool:
        normalized = path.replace("\\", "/").casefold()
        filename = normalized.rsplit("/", 1)[-1]
        in_test_directory = (
            normalized.startswith(("tests/", "__tests__/"))
            or "/tests/" in normalized
            or "/__tests__/" in normalized
        )
        return (
            in_test_directory
            or filename.startswith("test_")
            or filename.endswith("_test.py")
            or filename.endswith(javascript_test_suffixes)
        )

    test_cases: list[str] = []
    python_test_name = re.compile(
        r"^\s*(?:async\s+)?def\s+(test_[A-Za-z0-9_]+)\s*\(",
        re.MULTILINE,
    )
    javascript_test_title = re.compile(
        r"""\b(?:test|it)\s*\(\s*(['\"`])([^'\"`]+)\1""",
        re.IGNORECASE,
    )
    for path, content in files.items():
        if not is_test_path(path):
            continue
        test_cases.extend(match.group(1) for match in python_test_name.finditer(content))
        test_cases.extend(match.group(2) for match in javascript_test_title.finditer(content))

    if not test_cases:
        return []  # Missing/empty-test policies report these separately.

    issues: list[str] = []
    for feature, objective_aliases, test_aliases in _MISSION_FEATURES:
        if not objective_words.intersection(objective_aliases):
            continue
        has_named_case = any(words(case).intersection(test_aliases) for case in test_cases)
        if not has_named_case:
            issues.append(
                f"Mission explicitly requests '{feature}', but no generated test case "
                "name or title identifies this workflow. Add a clearly named behavioral test."
            )
    return issues

def find_missing_product_tests(files: Mapping[str, str]) -> list[str]:
    """Require at least one conventional automated test module for broad projects.

    Recognize common Python and JavaScript/TypeScript test naming conventions so
    frontend-first projects are not rejected merely because they use Vitest,
    Jest, or another JS test runner instead of pytest.
    """
    python_suffixes = (".py",)
    javascript_suffixes = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
    test_modules = []
    for path in files:
        normalized = path.replace("\\", "/").casefold()
        filename = normalized.rsplit("/", 1)[-1]
        if filename.endswith(python_suffixes) and (
            filename.startswith("test_") or filename.endswith("_test.py")
        ):
            test_modules.append(path)
            continue
        is_test_directory = normalized.startswith(("tests/", "__tests__/")) or "/__tests__/" in normalized
        if filename.endswith(javascript_suffixes) and (
            (is_test_directory and filename.startswith("test_"))
            or filename.endswith((
                "_test.js", "_test.jsx", "_test.mjs", "_test.cjs",
                "_test.ts", "_test.tsx", "_test.mts", "_test.cts",
                ".test.js", ".test.jsx", ".test.mjs", ".test.cjs",
                ".test.ts", ".test.tsx", ".test.mts", ".test.cts",
                ".spec.js", ".spec.jsx", ".spec.mjs", ".spec.cjs",
                ".spec.ts", ".spec.tsx", ".spec.mts", ".spec.cts",
            ))
        ):
            test_modules.append(path)
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


def test_feature_traceability_ignores_comments_and_helper_names_as_coverage() -> None:
    objective = "Create and delete records."
    issues = find_uncovered_mission_features(
        objective,
        {
            "tests/test_records.py": (
                "# test_create_record and test_delete_record are planned here\\n"
                "def create_record():\\n    return {}\\n"
                "def delete_record():\\n    return True\\n"
                "def test_records_are_available():\\n    assert True\\n"
            ),
        },
    )

    assert any("create" in issue for issue in issues)
    assert any("delete/remove" in issue for issue in issues)


def test_feature_traceability_accepts_named_javascript_test_titles() -> None:
    objective = "Create and delete records."
    issues = find_uncovered_mission_features(
        objective,
        {
            "src/records.spec.mjs": (
                "test('creates a record', () => { expect(createRecord()).toBeTruthy(); });\\n"
                "it('deletes a record', () => { expect(deleteRecord()).toBe(true); });"
            ),
        },
    )

    assert issues == []
