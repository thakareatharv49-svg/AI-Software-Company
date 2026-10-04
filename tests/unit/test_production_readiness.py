from pathlib import Path

from src.company.production.readiness import (
    ProductionReadiness,
    ReadinessReport,
)


def prepare_project(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".git").mkdir()


def test_production_readiness_reports_ready_for_valid_project(
    tmp_path: Path,
) -> None:
    prepare_project(tmp_path)

    readiness = ProductionReadiness(project_root=tmp_path)
    report = readiness.run()

    assert report.ready is True
    assert report.failed_required == []
    assert len(report.checks) == 6


def test_production_readiness_detects_missing_source_tree(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()

    readiness = ProductionReadiness(project_root=tmp_path)
    report = readiness.run()

    assert report.ready is False
    assert any(
        check.name == "source_tree" and not check.passed
        for check in report.checks
    )


def test_production_readiness_detects_missing_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prepare_project(tmp_path)

    monkeypatch.delenv(
        "PHASE14_TEST_REQUIRED",
        raising=False,
    )

    readiness = ProductionReadiness(project_root=tmp_path)
    report = readiness.run(
        required_environment=["PHASE14_TEST_REQUIRED"],
    )

    check = next(
        check
        for check in report.checks
        if check.name == "required_environment"
    )

    assert report.ready is False
    assert check.passed is False
    assert check.required is True
    assert "PHASE14_TEST_REQUIRED" in check.detail


def test_production_readiness_accepts_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prepare_project(tmp_path)

    monkeypatch.setenv(
        "PHASE14_TEST_REQUIRED",
        "configured",
    )

    readiness = ProductionReadiness(project_root=tmp_path)
    report = readiness.run(
        required_environment=["PHASE14_TEST_REQUIRED"],
    )

    check = next(
        check
        for check in report.checks
        if check.name == "required_environment"
    )

    assert report.ready is True
    assert check.passed is True


def test_production_readiness_custom_check() -> None:
    readiness = ProductionReadiness()

    passed = readiness.custom_check(
        "custom_pass",
        lambda: True,
    )
    failed = readiness.custom_check(
        "custom_fail",
        lambda: False,
    )

    assert passed.passed is True
    assert failed.passed is False


def test_production_readiness_custom_check_handles_exception() -> None:
    readiness = ProductionReadiness()

    result = readiness.custom_check(
        "custom_exception",
        lambda: 1 / 0,
    )

    assert result.passed is False
    assert "ZeroDivisionError" in result.detail


def test_readiness_report_serializes() -> None:
    readiness = ProductionReadiness()

    check = readiness.custom_check(
        "serialization",
        lambda: True,
    )

    report = ReadinessReport(
        ready=True,
        checks=[check],
    )

    data = report.as_dict()

    assert data["ready"] is True
    assert data["checks"][0]["name"] == "serialization"
    assert data["checks"][0]["passed"] is True
