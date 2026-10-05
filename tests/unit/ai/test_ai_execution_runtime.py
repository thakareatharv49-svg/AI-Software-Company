from company.ai.context import AIExecutionContext
from company.ai.runtime import (
    AIExecutionResult,
    AIExecutionRuntime,
    build_ai_execution_runtime,
    execute_ai_response,
)
from company.ai.tool_calling import AIToolCall, AIToolCallResponse


def test_runtime_executes_ai_response() -> None:
    result = execute_ai_response(
        AIToolCallResponse(
            text="execute",
            tool_calls=(
                AIToolCall(
                    "add",
                    {"a": 4, "b": 6},
                ),
            ),
        ),
        actor="runtime-test",
    )

    assert result.actor == "runtime-test"
    assert result.run_id
    assert result.loop.rounds == 1
    assert result.loop.exchanges[0].result.output == 10


def test_runtime_accepts_explicit_context() -> None:
    runtime = build_ai_execution_runtime()

    context = AIExecutionContext(
        run_id="run-test",
        actor="agent",
        metadata={"mission": "test"},
        max_tool_calls=2,
        max_rounds=1,
    )

    result = runtime.execute(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "echo",
                    {"text": "hello"},
                ),
            )
        ),
        context=context,
    )

    assert result.run_id == "run-test"
    assert result.actor == "agent"
    assert result.loop.exchanges[0].result.output == "hello"


def test_runtime_enforces_tool_call_limit() -> None:
    result = execute_ai_response(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "one"}),
                AIToolCall("echo", {"text": "two"}),
            )
        ),
        max_tool_calls=1,
    )

    assert len(result.loop.exchanges) == 1
    assert result.loop.stopped_by_limit is True


def test_runtime_enforces_round_limit() -> None:
    runtime = build_ai_execution_runtime()

    context = AIExecutionContext(
        max_tool_calls=10,
        max_rounds=1,
    )

    first = AIToolCallResponse(
        tool_calls=(
            AIToolCall("echo", {"text": "first"}),
        )
    )

    second = AIToolCallResponse(
        tool_calls=(
            AIToolCall("echo", {"text": "second"}),
        )
    )

    result = runtime.execute(
        first,
        context=context,
        next_response=lambda _response, _exchanges: second,
    )

    assert result.loop.rounds == 1
    assert result.loop.stopped_by_limit is True


def test_runtime_rejects_unknown_or_unsafe_tools() -> None:
    runtime = build_ai_execution_runtime()

    context = AIExecutionContext()

    result = runtime.execute(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "python",
                    {"code": "print(1)"},
                ),
            )
        ),
        context=context,
    )

    assert result.loop.exchanges[0].result.status == "failure"


def test_runtime_no_tool_response() -> None:
    result = execute_ai_response(
        AIToolCallResponse(text="No tools required.")
    )

    assert result.loop.rounds == 0
    assert result.loop.exchanges == ()
    assert result.loop.stopped_by_limit is False


def test_runtime_exports_exist() -> None:
    assert AIExecutionResult is not None
    assert AIExecutionRuntime is not None
    assert callable(build_ai_execution_runtime)
    assert callable(execute_ai_response)
