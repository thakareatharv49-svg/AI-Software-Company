from company.ai.orchestration import (
    AIOrchestrationResult,
    AIOrchestrationStep,
    AIToolOrchestrator,
    build_ai_tool_orchestrator,
)
from company.ai.tool_calling import (
    AIToolCall,
    AIToolCallResponse,
)


def test_orchestrator_executes_multiple_calls() -> None:
    orchestrator = build_ai_tool_orchestrator()

    result = orchestrator.execute(
        AIToolCallResponse(
            text="calculate",
            tool_calls=(
                AIToolCall("echo", {"text": "hello"}),
                AIToolCall("add", {"a": 2, "b": 3}),
            ),
        )
    )

    assert result.success is True
    assert len(result.steps) == 2
    assert result.steps[0].result.output == "hello"
    assert result.steps[1].result.output == 5


def test_orchestrator_preserves_model_text() -> None:
    orchestrator = build_ai_tool_orchestrator()

    result = orchestrator.execute(
        AIToolCallResponse(text="model response")
    )

    assert result.text == "model response"
    assert result.steps == ()


def test_orchestrator_reports_failure() -> None:
    orchestrator = build_ai_tool_orchestrator()

    result = orchestrator.execute(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "unknown",
                    {},
                ),
            )
        )
    )

    assert result.success is False
    assert result.steps[0].result.status == "failure"


def test_orchestration_exports_exist() -> None:
    assert AIOrchestrationResult is not None
    assert AIOrchestrationStep is not None
    assert AIToolOrchestrator is not None
    assert callable(build_ai_tool_orchestrator)
