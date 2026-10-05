from __future__ import annotations

from company.ai.tool_calling import (
    AIToolCall,
    build_ai_tool_calling_engine,
)


def test_ai_does_not_expose_arbitrary_execution() -> None:
    engine = build_ai_tool_calling_engine()

    tools = engine.available_tools()

    assert "shell" not in tools
    assert "python" not in tools
    assert "exec" not in tools
    assert "filesystem" not in tools


def test_ai_unknown_tool_cannot_bypass_m20() -> None:
    engine = build_ai_tool_calling_engine()

    exchange = engine.execute_call(
        AIToolCall(
            tool_name="shell",
            arguments={"command": "echo unsafe"},
        )
    )

    assert exchange.result.status == "failure"
    assert exchange.result.output is None
    assert exchange.result.error is not None


def test_ai_exposes_only_registered_tools() -> None:
    engine = build_ai_tool_calling_engine()

    assert set(engine.available_tools()) == {"echo", "add"}
