from src.company.recovery.service import RecoveryService


def test_recovery_records_stage_and_actionable_error_details() -> None:
    recovery = RecoveryService(max_attempts=2)

    result = recovery.record_failure(
        RuntimeError("generated API route failed"),
        project_id="project-1",
        stage="execution",
    )

    assert result.retryable
    assert result.action == "retry"
    assert result.stage == "execution"
    assert result.error_type == "RuntimeError"
    assert result.error_message == "generated API route failed"


def test_recovery_budgets_are_isolated_per_project_and_stage() -> None:
    recovery = RecoveryService(max_attempts=2)

    first = recovery.record_failure(ValueError("manifest invalid"), "project-1", "planning")
    second = recovery.record_failure(ValueError("manifest invalid"), "project-1", "planning")
    other_stage = recovery.record_failure(RuntimeError("QA failed"), "project-1", "qa")
    other_project = recovery.record_failure(RuntimeError("QA failed"), "project-2", "planning")

    assert first.retryable
    assert not second.retryable
    assert other_stage.retryable
    assert other_project.retryable
    assert recovery.attempts("project-1", "planning") == 2
    assert recovery.attempts("project-1", "qa") == 1
    assert recovery.attempts("project-2", "planning") == 1


def test_recovery_reset_can_clear_one_stage_or_all_project_stages() -> None:
    recovery = RecoveryService(max_attempts=3)
    recovery.record_failure(RuntimeError("QA failed"), "project-1", "qa")
    recovery.record_failure(RuntimeError("execution failed"), "project-1", "execution")
    recovery.record_failure(RuntimeError("other project"), "project-2", "qa")

    recovery.reset("project-1", "qa")
    assert recovery.attempts("project-1", "qa") == 0
    assert recovery.attempts("project-1", "execution") == 1

    recovery.reset("project-1")
    assert recovery.attempts("project-1", "execution") == 0
    assert recovery.attempts("project-2", "qa") == 1


def test_recovery_bounds_persisted_error_message_length() -> None:
    recovery = RecoveryService()
    result = recovery.record_failure(RuntimeError("x" * 5000), "project-1", "qa")

    assert len(result.error_message) == 2000
