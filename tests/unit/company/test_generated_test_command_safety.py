from src.company.project_generator import OllamaProjectGenerator


def test_generated_test_command_accepts_standard_local_pytest_commands():
    normalize = OllamaProjectGenerator._normalize_test_command

    assert normalize(["python", "-m", "pytest", "-q"]) == [
        "python", "-m", "pytest", "-q"
    ]
    assert normalize(["pytest", "-q"]) == ["pytest", "-q"]
    assert normalize(["python3", "-m", "unittest"]) == [
        "python3", "-m", "unittest"
    ]


def test_generated_test_command_rejects_arbitrary_pytest_arguments():
    normalize = OllamaProjectGenerator._normalize_test_command
    default = ["python", "-m", "pytest", "-q"]

    assert normalize(["pytest", "/tmp/untrusted_test.py"]) == default
    assert normalize(["pytest", "-p", "unexpected_plugin"]) == default
    assert normalize(["python", "-m", "pytest", "-c", "../pytest.ini"]) == default
    assert normalize(["python", "-c", "import os; os.remove('data')"]) == default
    assert normalize(["curl", "https://example.invalid/script"]) == default


def test_generated_test_command_rejects_empty_and_non_list_values():
    normalize = OllamaProjectGenerator._normalize_test_command
    default = ["python", "-m", "pytest", "-q"]

    assert normalize([]) == default
    assert normalize(None) == default
    assert normalize("pytest -q") == default
