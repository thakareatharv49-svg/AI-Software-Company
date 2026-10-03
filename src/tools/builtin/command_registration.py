from src.agents.models.enums import AgentPermission
from src.tools.builtin.commands import CommandTools
from src.tools.models.contracts import ToolDefinition
from src.tools.registry.registry import ToolRegistry


def register_command_tools(
    registry: ToolRegistry,
    workspace: str,
) -> None:
    tools = CommandTools(workspace)

    registry.register(
        ToolDefinition(
            name="run_command",
            description="Run an allowlisted command inside the workspace.",
            permission=AgentPermission.RUN_COMMANDS,
            handler=tools.run_command,
        )
    )
