from __future__ import annotations

from company.agents.tool_integration import build_safe_agent_tool_runner
from company.agents.tool_runner import AgentToolRequest


def test_agent_uses_m20_execution_boundary() -> None:
    runner = build_safe_agent_tool_runner()

    execution = runner.run(
        AgentToolRequest(
            tool_name="echo",
            arguments={"text": "permission-check"},
        )
    )

    assert execution.outcome.result.status.value == "success"


def test_agent_does_not_expose_arbitrary_execution() -> None:
    runner = build_safe_agent_tool_runner()

    tools = runner.list_tools()

    assert "shell" not in tools
    assert "python" not in tools
    assert "exec" not in tools
    assert "filesystem" not in tools


def test_unknown_execution_is_not_exposed() -> None:
    runner = build_safe_agent_tool_runner()

    assert "unknown-tool" not in runner.list_tools()
