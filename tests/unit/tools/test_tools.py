from src.agents.execution.context import AgentExecutionContext
from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission
from src.tools.execution.executor import ToolExecutor
from src.tools.models.contracts import ToolDefinition, ToolRequest
from src.tools.models.enums import ToolPermission
from src.tools.registry.registry import ToolRegistry


def test_tool_registry():
    registry = ToolRegistry()

    tool = ToolDefinition(
        name="echo",
        description="Echo text",
        permission=ToolPermission.READ_FILES,
        handler=lambda text: text,
    )

    registry.register(tool)

    assert registry.get("echo") is tool
    assert len(registry.list_tools()) == 1


def test_tool_executor_allows_granted_permission():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo text",
            permission=ToolPermission.READ_FILES,
            handler=lambda text: text,
        )
    )

    agent = AgentDefinition(
        name="engineer",
        role="engineer",
        capabilities=["coding"],
        permissions={AgentPermission.READ_FILES},
    )

    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions={AgentPermission.READ_FILES},
    )

    result = ToolExecutor(registry).execute(
        context,
        ToolRequest(
            tool_name="echo",
            arguments={"text": "hello"},
        ),
    )

    assert result.success is True
    assert result.output == "hello"


def test_tool_executor_blocks_missing_permission():
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="danger",
            description="Restricted operation",
            permission=ToolPermission.GIT_PUSH,
            handler=lambda: "pushed",
        )
    )

    agent = AgentDefinition(
        name="engineer",
        role="engineer",
        capabilities=["coding"],
        permissions={AgentPermission.READ_FILES},
    )

    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions={AgentPermission.READ_FILES},
    )

    result = ToolExecutor(registry).execute(
        context,
        ToolRequest(tool_name="danger"),
    )

    assert result.success is False
    assert "does not have permission" in result.error
