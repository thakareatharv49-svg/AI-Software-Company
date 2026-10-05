from __future__ import annotations

from company.agents.tool_integration import build_safe_agent_tool_runner
from company.agents.tool_runner import AgentToolRequest
from company.tools.models import ToolStatus


def test_agent_can_discover_registered_tools() -> None:
    runner = build_safe_agent_tool_runner()

    assert runner.list_tools() == ("echo", "add")


def test_agent_can_execute_echo_tool() -> None:
    runner = build_safe_agent_tool_runner()

    execution = runner.run(
        AgentToolRequest(
            tool_name="echo",
            arguments={"text": "hello"},
        )
    )

    assert execution.outcome.result.status == ToolStatus.SUCCESS
    assert execution.outcome.result.output == "hello"


def test_agent_can_execute_add_tool() -> None:
    runner = build_safe_agent_tool_runner()

    execution = runner.run(
        AgentToolRequest(
            tool_name="add",
            arguments={"a": 10, "b": 7},
        )
    )

    assert execution.outcome.result.status == ToolStatus.SUCCESS
    assert execution.outcome.result.output == 17


def test_agent_unknown_tool_fails_safely() -> None:
    runner = build_safe_agent_tool_runner()

    execution = runner.run(
        AgentToolRequest(
            tool_name="unknown-tool",
            arguments={},
        )
    )

    assert execution.outcome.result.status == ToolStatus.FAILURE
    assert execution.outcome.result.error is not None


def test_agent_arguments_are_isolated() -> None:
    runner = build_safe_agent_tool_runner()

    arguments = {"text": "stable"}

    request = AgentToolRequest(
        tool_name="echo",
        arguments=arguments,
    )

    arguments["text"] = "changed"

    execution = runner.run(request)

    assert execution.outcome.result.output == "stable"


def test_agent_receives_validation_failure_safely() -> None:
    runner = build_safe_agent_tool_runner()

    execution = runner.run(
        AgentToolRequest(
            tool_name="echo",
            arguments={"text": 123},
        )
    )

    assert execution.outcome.result.status == ToolStatus.FAILURE
    assert execution.outcome.result.error is not None
