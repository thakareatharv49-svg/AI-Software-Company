from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_m86_large_project_benchmark import (
    BenchmarkError,
    _stage_evidence,
    _test_evidence,
    evaluate_case,
    load_catalog,
)


def test_runner_loads_three_distinct_versioned_cases() -> None:
    cases = load_catalog(Path("tests/fixtures/large_project_benchmark_cases.json"))
    assert {case["project_type"] for case in cases} >= {
        "web_application", "api_application", "cli_utility"
    }
    assert len({case["id"] for case in cases}) == len(cases)


def test_runner_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    catalog = {
        "schema_version": 1,
        "cases": [
            {"id": "same", "expected_files": []},
            {"id": "same", "expected_files": []},
        ],
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(BenchmarkError, match="Duplicate benchmark case id"):
        load_catalog(path)


@pytest.mark.parametrize("unsafe", ["../escape.py", "/absolute.py", "src\\escape.py"])
def test_runner_rejects_unsafe_expected_paths(tmp_path: Path, unsafe: str) -> None:
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "cases": [{"id": "safe-check", "expected_files": [unsafe]}],
    }), encoding="utf-8")
    with pytest.raises(BenchmarkError, match="Unsafe expected artifact path"):
        load_catalog(path)


def test_stage_evidence_preserves_stage_status_and_failure_reason() -> None:
    evidence = _stage_evidence({"steps": [
        {"title": "Build", "status": "completed", "attempts": 1},
        {"name": "QA", "status": "failed", "last_error": "exit code 1"},
    ]})
    assert evidence == [
        {"name": "Build", "status": "completed", "attempts": 1, "error": None},
        {"name": "QA", "status": "failed", "attempts": 0, "error": "exit code 1"},
    ]


def test_test_evidence_preserves_actual_qa_exit_code_and_command() -> None:
    evidence = _test_evidence({
        "qa_status": "failed",
        "qa_exit_code": 1,
        "qa_command": ["python", "-m", "pytest", "-q"],
        "qa_evidence": "Factory QA runner result: exit_code=1",
    })
    assert evidence is not None
    assert evidence["qa_exit_code"] == 1
    assert evidence["qa_command"] == ["python", "-m", "pytest", "-q"]


def test_evaluator_reports_missing_files_and_missing_test_evidence(tmp_path: Path) -> None:
    case = {
        "expected_files": ["README.md", "src/app.py"],
        "required_features": ["create", "update"],
    }
    (tmp_path / "README.md").write_text("Inventory API", encoding="utf-8")
    checks = evaluate_case(case, ["README.md"], {}, "completed", workspace=tmp_path)
    by_id = {item["id"]: item for item in checks}
    assert by_id["factory_terminal_success"]["passed"] is True
    assert by_id["required_files"]["passed"] is False
    assert "src/app.py" in by_id["required_files"]["detail"]
    assert by_id["required_features"]["passed"] is False
    assert by_id["test_command_exit_code"]["passed"] is False


def test_evaluator_checks_workspace_feature_markers_and_zero_exit_code(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def create_item():\n    def update_item(): pass\n", encoding="utf-8")
    case = {"expected_files": ["app.py"], "required_features": ["create", "update"]}
    checks = evaluate_case(case, ["app.py"], {"qa_exit_code": 0}, "completed", workspace=tmp_path)
    by_id = {item["id"]: item for item in checks}
    assert all(item["passed"] for item in by_id.values())


def test_exit_code_can_be_recovered_from_persisted_qa_evidence() -> None:
    checks = evaluate_case(
        {"expected_files": [], "required_features": []},
        [],
        {"qa_evidence": "Factory QA runner result: status=passed; exit_code=0; duration_ms=12"},
        "completed",
    )
    by_id = {item["id"]: item for item in checks}
    assert by_id["test_command_exit_code"]["passed"] is True
