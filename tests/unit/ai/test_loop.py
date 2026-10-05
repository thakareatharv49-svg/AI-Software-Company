from company.ai.context import AIExecutionContext
from company.ai.loop import AIToolCallingLoop
from company.ai.tool_calling import (
    AIToolCall,
    AIToolCallResponse,
    build_ai_tool_calling_engine,
)


def test_loop_executes_tool_calls() -> None:
    loop = AIToolCallingLoop(
        build_ai_tool_calling_engine()
    )

    result = loop.run(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "echo",
                    {"text": "hello"},
                ),
            )
        ),
        context=AIExecutionContext(
            max_tool_calls=2,
            max_rounds=2,
        ),
    )

    assert result.rounds == 1
    assert result.stopped_by_limit is False
    assert len(result.exchanges) == 1
    assert result.exchanges[0].result.output == "hello"


def test_loop_enforces_tool_call_limit() -> None:
    loop = AIToolCallingLoop(
        build_ai_tool_calling_engine()
    )

    result = loop.run(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "one"}),
                AIToolCall("echo", {"text": "two"}),
            )
        ),
        context=AIExecutionContext(
            max_tool_calls=1,
            max_rounds=2,
        ),
    )

    assert len(result.exchanges) == 1
    assert result.stopped_by_limit is True


def test_loop_enforces_round_limit() -> None:
    loop = AIToolCallingLoop(
        build_ai_tool_calling_engine()
    )

    responses = [
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "first"}),
            )
        ),
        AIToolCallResponse(
            tool_calls=(
                AIToolCall("echo", {"text": "second"}),
            )
        ),
    ]

    index = 0

    def next_response(
        _response: AIToolCallResponse,
        _exchanges: tuple,
    ) -> AIToolCallResponse:
        nonlocal index
        response = responses[index]
        index += 1
        return response

    result = loop.run(
        responses[0],
        context=AIExecutionContext(
            max_tool_calls=10,
            max_rounds=1,
        ),
        next_response=next_response,
    )

    assert result.rounds == 1
    assert result.stopped_by_limit is True


def test_loop_without_tool_calls_does_nothing() -> None:
    loop = AIToolCallingLoop(
        build_ai_tool_calling_engine()
    )

    result = loop.run(
        AIToolCallResponse(text="done"),
        context=AIExecutionContext(),
    )

    assert result.rounds == 0
    assert result.exchanges == ()
    assert result.stopped_by_limit is False


def test_loop_preserves_security_boundary() -> None:
    loop = AIToolCallingLoop(
        build_ai_tool_calling_engine()
    )

    result = loop.run(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "shell",
                    {"command": "whoami"},
                ),
            )
        ),
        context=AIExecutionContext(),
    )

    assert result.exchanges[0].result.status == "failure"
