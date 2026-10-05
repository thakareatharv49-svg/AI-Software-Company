from __future__ import annotations

from company.ai.tool_calling import (
    AIToolCall,
    AIToolCallResponse,
    AIToolCallTranslator,
    build_ai_tool_calling_engine,
)


def test_ai_can_discover_agent_tools() -> None:
    engine = build_ai_tool_calling_engine()

    assert engine.available_tools() == ("echo", "add")


def test_ai_tool_call_executes_echo() -> None:
    engine = build_ai_tool_calling_engine()

    exchange = engine.execute_call(
        AIToolCall(
            tool_name="echo",
            arguments={"text": "hello-ai"},
        )
    )

    assert exchange.result.status == "success"
    assert exchange.result.output == "hello-ai"
    assert exchange.result.error is None


def test_ai_tool_call_executes_add() -> None:
    engine = build_ai_tool_calling_engine()

    exchange = engine.execute_call(
        AIToolCall(
            tool_name="add",
            arguments={"a": 20, "b": 22},
        )
    )

    assert exchange.result.status == "success"
    assert exchange.result.output == 42


def test_ai_unknown_tool_fails_safely() -> None:
    engine = build_ai_tool_calling_engine()

    exchange = engine.execute_call(
        AIToolCall(
            tool_name="unknown-tool",
        )
    )

    assert exchange.result.status == "failure"
    assert exchange.result.error is not None


def test_ai_validation_failure_is_returned() -> None:
    engine = build_ai_tool_calling_engine()

    exchange = engine.execute_call(
        AIToolCall(
            tool_name="echo",
            arguments={"text": 123},
        )
    )

    assert exchange.result.status == "failure"
    assert exchange.result.error is not None


def test_ai_response_executes_multiple_tools() -> None:
    engine = build_ai_tool_calling_engine()

    response = AIToolCallResponse(
        text="execute requested tools",
        tool_calls=(
            AIToolCall(
                tool_name="echo",
                arguments={"text": "first"},
            ),
            AIToolCall(
                tool_name="add",
                arguments={"a": 2, "b": 3},
            ),
        ),
    )

    exchanges = engine.execute_response(response)

    assert len(exchanges) == 2
    assert exchanges[0].result.output == "first"
    assert exchanges[1].result.output == 5


def test_ai_arguments_are_isolated() -> None:
    engine = build_ai_tool_calling_engine()

    arguments = {"text": "stable"}

    call = AIToolCall(
        tool_name="echo",
        arguments=arguments,
    )

    arguments["text"] = "changed"

    exchange = engine.execute_call(call)

    assert exchange.result.output == "stable"


def test_translator_preserves_result() -> None:
    engine = build_ai_tool_calling_engine()

    call = AIToolCall(
        tool_name="echo",
        arguments={"text": "translator"},
    )

    request = AIToolCallTranslator.to_agent_request(call)

    execution = engine._runner.run(request)

    result = AIToolCallTranslator.from_agent_execution(
        call,
        execution,
    )

    assert result.tool_name == "echo"
    assert result.status == "success"
    assert result.output == "translator"
