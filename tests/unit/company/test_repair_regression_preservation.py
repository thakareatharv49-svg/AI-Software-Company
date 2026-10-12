from src.company.project_generator import OllamaProjectGenerator


def test_full_repair_preserves_existing_regression_tests_and_keeps_new_files():
    original = {
        "app.js": "broken implementation",
        "tests/test_core.py": "def test_core():\n    assert 1 + 1 == 2\n",
        "tests/test_edge_cases.py": "def test_edge_case():\n    assert not []\n",
    }
    repaired = {
        "app.js": "fixed implementation",
        "tests/test_core.py": "def test_core():\n    assert True\n",
        "tests/test_new.py": "def test_new():\n    assert 'ready'\n",
    }

    result = OllamaProjectGenerator._preserve_regression_tests(original, repaired)

    assert result["app.js"] == "fixed implementation"
    assert result["tests/test_core.py"] == original["tests/test_core.py"]
    assert result["tests/test_edge_cases.py"] == original["tests/test_edge_cases.py"]
    assert result["tests/test_new.py"] == repaired["tests/test_new.py"]


def test_explicitly_targeted_test_can_be_repaired_but_not_deleted():
    original = {"tests/test_core.py": "def test_core(): pass"}
    repaired = {"tests/test_core.py": "def test_core(): assert True"}

    changed = OllamaProjectGenerator._preserve_regression_tests(
        original, repaired, allow_test_changes=True
    )
    missing = OllamaProjectGenerator._preserve_regression_tests(
        original, {}, allow_test_changes=True
    )

    assert changed["tests/test_core.py"] == repaired["tests/test_core.py"]
    assert missing["tests/test_core.py"] == original["tests/test_core.py"]
