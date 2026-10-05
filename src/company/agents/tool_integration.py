from __future__ import annotations

from typing import Any

from company.agents.tool_runner import AgentToolRequest, AgentToolRunner
from company.agents.tools import AgentToolInterface
from company.tools.deterministic import AddTool, EchoTool
from company.tools.executor import ToolExecutor
from company.tools.registry import ToolRegistry


def build_safe_agent_tool_runner() -> AgentToolRunner:
    """Build the prevention-first agent tool boundary."""

    registry = ToolRegistry()

    registry.register(EchoTool())
    registry.register(AddTool())

    executor = ToolExecutor(registry=registry)

    interface = AgentToolInterface(
        registry=registry,
        executor=executor,
    )

    return AgentToolRunner(interface)


def execute_agent_tool(
    tool_name: str,
    arguments: dict[str, Any],
):
    runner = build_safe_agent_tool_runner()

    execution = runner.run(
        AgentToolRequest(
            tool_name=tool_name,
            arguments=arguments,
        )
    )

    return execution.outcome.result
