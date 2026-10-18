from types import SimpleNamespace

from src.company.autonomous_factory_runner import FactoryAutonomousRunner


def _result(*, stdout: str = "", stderr: str = "", summary: str = ""):
    return SimpleNamespace(
        pipeline=SimpleNamespace(
            qa_result=SimpleNamespace(
                status="failed",
                exit_code=1,
                duration_ms=125,
                stdout=stdout,
                stderr=stderr,
            ),
            review_result=SimpleNamespace(
                status="approved",
                approved=True,
                summary=summary,
            ),
        )
    )


def test_quality_evidence_includes_bounded_redacted_test_output():
    secret = "ghp_" + "A" * 32
    result = _result(
        stdout=f"assertion failed password=super-secret {secret}",
        stderr="Traceback: expected 2, got 1",
        summary=f"review token={secret}",
    )

    evidence = FactoryAutonomousRunner._quality_evidence_updates(
        result,
        ["pytest", "-q", "--token", secret],
    )

    assert evidence["qa_status"] == "failed"
    assert evidence["qa_exit_code"] == 1
    assert "assertion failed" in evidence["qa_evidence"]
    assert "expected 2, got 1" in evidence["qa_evidence"]
    assert "super-secret" not in evidence["qa_evidence"]
    assert secret not in evidence["qa_evidence"]
    assert secret not in str(evidence["qa_command"])
    assert secret not in evidence["security_summary"]
    assert "[REDACTED_TOKEN]" in evidence["qa_evidence"]


def test_quality_evidence_caps_subprocess_output_and_security_summary():
    result = _result(
        stdout="x" * 5000,
        stderr="y" * 5000,
        summary="z" * 5000,
    )

    evidence = FactoryAutonomousRunner._quality_evidence_updates(result, ["pytest"])

    assert len(evidence["qa_evidence"]) <= 5200
    assert len(evidence["security_summary"]) == 1000
    assert len(evidence["security_evidence"]) <= 1100
    assert evidence["qa_duration_ms"] == 125


def test_stage_progress_redacts_and_bounds_durable_failure_details():
    from types import SimpleNamespace

    secret = "ghp_" + "Q" * 32
    qa_step = SimpleNamespace(stage=SimpleNamespace(value="qa"), status="planned", detail=None)
    plan = SimpleNamespace(steps=[qa_step])

    FactoryAutonomousRunner._record_stage_progress(
        plan,
        "engineering_qa_security_github",
        "failed",
        f"QA failed: password=super-secret token={secret} " + ("x" * 5000),
    )

    assert qa_step.status == "failed"
    assert "super-secret" not in qa_step.detail
    assert secret not in qa_step.detail
    assert "[REDACTED_TOKEN]" in qa_step.detail
    assert len(qa_step.detail) <= 4000


def test_runner_failure_diagnostics_redact_secrets():
    from types import SimpleNamespace

    secret = "ghp_" + "R" * 32
    execution_step = SimpleNamespace(
        stage=SimpleNamespace(value="execution"),
        status="running",
        detail=None,
    )
    plan = SimpleNamespace(steps=[execution_step])

    FactoryAutonomousRunner._record_runner_failure(
        plan,
        RuntimeError(f"generation crashed password=super-secret token={secret}"),
    )

    assert execution_step.status == "failed"
    assert "super-secret" not in execution_step.detail
    assert secret not in execution_step.detail
    assert "[REDACTED_TOKEN]" in execution_step.detail


def test_quality_evidence_includes_browser_acceptance_summary():
    result = _result(stdout="tests passed")
    result.pipeline.browser_acceptance = {
        "status": "passed",
        "routes_checked": ["/", "/settings"],
        "interactions_checked": ["Save"],
        "detail": "Routes and safe interaction passed.",
    }

    evidence = FactoryAutonomousRunner._quality_evidence_updates(result, ["pytest"])

    assert "browser_status=passed" in evidence["qa_evidence"]
    assert "routes=/,/settings" in evidence["qa_evidence"]
    assert "interactions=Save" in evidence["qa_evidence"]
