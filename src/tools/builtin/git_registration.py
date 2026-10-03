from src.agents.models.enums import AgentPermission
from src.tools.builtin.git import GitTools
from src.tools.models.contracts import ToolDefinition
from src.tools.registry.registry import ToolRegistry


def register_git_tools(
    registry: ToolRegistry,
    workspace: str,
) -> None:
    tools = GitTools(workspace)

    registry.register(
        ToolDefinition(
            name="git_status",
            description="Show the current Git working-tree status.",
            permission=AgentPermission.READ_FILES,
            handler=tools.status,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_diff",
            description="Show the current Git diff.",
            permission=AgentPermission.READ_FILES,
            handler=tools.diff,
        )
    )
