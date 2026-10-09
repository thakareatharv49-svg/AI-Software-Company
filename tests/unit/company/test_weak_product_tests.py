from src.company.product_quality import find_weak_product_tests


def test_rejects_tautological_generated_assertions() -> None:
    issues = find_weak_product_tests(
        {"tests/test_project.py": "def test_app():\n    assert True\n"}
    )

    assert len(issues) == 1
    assert "tautological assertion" in issues[0]


def test_rejects_constant_equality_in_generated_tests() -> None:
    issues = find_weak_product_tests(
        {"test_project.py": "def test_app():\n    assert 1 == 1\n"}
    )

    assert len(issues) == 1


def test_accepts_tests_that_assert_real_behavior() -> None:
    issues = find_weak_product_tests(
        {
            "tests/test_project.py": (
                "def add(a, b):\n"
                "    return a + b\n\n"
                "def test_adds_values():\n"
                "    assert add(2, 3) == 5\n"
            )
        }
    )

    assert issues == []


def test_ignores_tautologies_in_documentation_and_application_source() -> None:
    issues = find_weak_product_tests(
        {
            "docs/example.py": "assert True\n",
            "app.py": "assert True\n",
            "app.js": "const x = true;\n",
        }
    )

    assert issues == []
