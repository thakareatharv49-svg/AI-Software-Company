from __future__ import annotations

from src.company.product_quality import (
    find_unfinished_product_content,
    find_weak_product_tests,
)


def test_detects_obvious_placeholder_copy_in_generated_ui() -> None:
    issues = find_unfinished_product_content({
        "index.html": "<main><h1>Coming soon</h1></main>",
        "app.js": "startApp();",
    })

    assert len(issues) == 1
    assert "index.html" in issues[0]
    assert "unfinished placeholder text" in issues[0]


def test_ignores_legitimate_todo_labels_and_input_placeholders() -> None:
    issues = find_unfinished_product_content({
        "index.html": '<label>To-do list</label><input placeholder="Add a task">',
        "app.js": 'const label = "TODO";',
    })

    assert issues == []


def test_ignores_tests_and_documentation() -> None:
    issues = find_unfinished_product_content({
        "tests/test_copy.py": 'assert "coming soon" in source',
        "docs/README.md": "Lorem ipsum is a placeholder example.",
    })

    assert issues == []


def test_detects_unimplemented_feature_copy_in_javascript() -> None:
    issues = find_unfinished_product_content({
        "app.js": 'showMessage("Feature not available yet");',
    })

    assert len(issues) == 1
    assert "app.js" in issues[0]

    
def test_rejects_assertions_that_compare_only_literal_values() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": "def test_title():\n    assert \"Expense Tracker\" in \"Expense Tracker\"\n"
    })

    assert len(issues) == 1
    assert "tautological assertion" in issues[0]


def test_accepts_assertions_that_exercise_runtime_values() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": (
            "def test_total_uses_expenses():\n"
            "    expenses = [{\"amount\": 12}, {\"amount\": 8}]\n"
            "    total = sum(item[\"amount\"] for item in expenses)\n"
            "    assert total == 20\n"
            "    assert total != 0\n"
        )
    })

    assert issues == []


def test_rejects_constant_boolean_assertion() -> None:
    issues = find_weak_product_tests({
        "tests/test_app.py": "def test_app():\n    assert True\n"
    })

    assert len(issues) == 1
