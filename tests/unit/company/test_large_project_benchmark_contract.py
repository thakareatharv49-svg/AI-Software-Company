from __future__ import annotations

import json
from pathlib import PurePosixPath

import pytest

from src.company.artifact_validation import validate_generated_artifacts


CATALOG_PATH = "tests/fixtures/large_project_benchmark_cases.json"
REQUIRED_CASE_FIELDS = {
    "id",
    "project_type",
    "mission",
    "expected_files",
    "required_features",
    "test_command",
    "acceptance_checks",
}


@pytest.fixture(scope="module")
def catalog() -> dict:
    with open(CATALOG_PATH, encoding="utf-8") as benchmark_file:
        return json.load(benchmark_file)


def test_benchmark_catalog_is_versioned_and_nonempty(catalog: dict) -> None:
    assert catalog["schema_version"] == 1
    assert catalog["cases"], "The benchmark must include at least one project case."


def test_benchmark_covers_distinct_project_types(catalog: dict) -> None:
    cases = catalog["cases"]
    assert {case["project_type"] for case in cases} >= {
        "web_application",
        "api_application",
        "cli_utility",
    }
    assert len({case["id"] for case in cases}) == len(cases)


@pytest.mark.parametrize("case_index", [0, 1, 2])
def test_each_case_has_a_complete_testable_contract(catalog: dict, case_index: int) -> None:
    case = catalog["cases"][case_index]
    assert REQUIRED_CASE_FIELDS <= case.keys()
    assert case["mission"].strip()
    assert case["expected_files"]
    assert case["required_features"]
    assert case["acceptance_checks"] == [
        "artifact_safety",
        "required_files",
        "required_features",
        "test_command_exit_code",
    ]
    assert case["test_command"] and case["test_command"][0] in {"python", "python3"}


def test_benchmark_expected_paths_are_safe_relative_paths(catalog: dict) -> None:
    for case in catalog["cases"]:
        for path in case["expected_files"]:
            pure_path = PurePosixPath(path)
            assert not pure_path.is_absolute(), (case["id"], path)
            assert ".." not in pure_path.parts, (case["id"], path)
            assert "\\\\" not in path, (case["id"], path)


def test_artifact_safety_check_reports_a_precise_failure() -> None:
    issues = validate_generated_artifacts(
        {
            "index.html": '<!doctype html><script src="missing.js"></script>',
            "../outside.txt": "must not escape the workspace",
        }
    )
    assert any("not a safe relative path" in issue for issue in issues)
    assert any("missing local asset" in issue for issue in issues)
