from src.company.execution.pipeline import CompanyExecutionPipeline
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


def test_recovery_stops_repeating_the_same_failure_before_budget_exhaustion() -> None:
    recovery = RecoveryService(max_attempts=4)

    first = recovery.record_failure(
        RuntimeError("QA failed for project project-a: missing app.js"),
        stage="qa",
    )
    repeated = recovery.record_failure(
        RuntimeError("QA failed for project project-b: missing app.js"),
        stage="qa",
    )

    assert first.retryable
    assert not first.repeated_failure
    assert not repeated.retryable
    assert repeated.repeated_failure
    assert repeated.action == "block_repeated_failure"
    assert repeated.attempt == 2


def test_recovery_reset_allows_retrying_a_failure_after_inputs_change() -> None:
    recovery = RecoveryService(max_attempts=3)
    recovery.record_failure(RuntimeError("artifact missing"), stage="artifacts")
    repeated = recovery.record_failure(RuntimeError("artifact missing"), stage="artifacts")
    assert repeated.repeated_failure

    recovery.reset()
    fresh = recovery.record_failure(RuntimeError("artifact missing"), stage="artifacts")

    assert fresh.attempt == 1
    assert fresh.retryable
    assert not fresh.repeated_failure

def test_pipeline_classifies_failures_into_recovery_stages() -> None:
    classify = CompanyExecutionPipeline._classify_recovery_stage

    assert classify(RuntimeError("QA failed: assertion mismatch")) == "qa"
    assert classify(RuntimeError("Code review failed: unsafe input")) == "security"
    assert classify(RuntimeError("Generated artifacts failed validation")) == "artifacts"
    assert classify(RuntimeError("GitHub rate limit exceeded")) == "github"
    assert classify(RuntimeError("agent execution crashed")) == "execution"

def test_generated_python_test_discovery_includes_root_and_source_tests() -> None:
    detect = CompanyExecutionPipeline._has_generated_python_tests

    assert detect({"test_app.py": "def test_app(): pass"})
    assert detect({"src/test_service.py": "def test_service(): pass"})
    assert detect({"src/service_test.py": "def test_service(): pass"})
    assert detect({"tests/custom_suite.py": "def suite(): pass"})
    assert not detect({"src/service.py": "def service(): pass"})


def test_generated_javascript_test_discovery_includes_source_tests() -> None:
    detect = CompanyExecutionPipeline._has_generated_javascript_tests

    assert detect({"src/app.test.js": "test('works', () => {})"})
    assert detect({"specs/app.spec.js": "test('works', () => {})"})
    assert not detect({"src/app.js": "export const value = 1"})


def test_generated_javascript_test_discovery_supports_common_node_module_formats() -> None:
    detect = CompanyExecutionPipeline._has_generated_javascript_tests

    assert detect({"tests/api.test.cjs": "test('works', () => {})"})
    assert detect({"src/api.spec.mjs": "test('works', () => {})"})
    assert detect({"tests/ui.test.js": "test('works', () => {})"})
    assert not detect({"src/app.cjs": "module.exports = {}"})
    assert not detect({"src/app.mjs": "export const value = 1"})
