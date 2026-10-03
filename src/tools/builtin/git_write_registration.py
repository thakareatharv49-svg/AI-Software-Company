from src.agents.models.enums import AgentPermission
from src.tools.builtin.git_write import GitWriteTools
from src.tools.models.contracts import ToolDefinition
from src.tools.registry.registry import ToolRegistry


def register_git_write_tools(
    registry: ToolRegistry,
    workspace: str,
) -> None:
    tools = GitWriteTools(workspace)

    registry.register(
        ToolDefinition(
            name="git_commit",
            description="Stage all workspace changes and create a Git commit.",
            permission=AgentPermission.GIT_COMMIT,
            handler=tools.commit,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_push",
            description="Push the current Git branch to a remote.",
            permission=AgentPermission.GIT_PUSH,
            handler=tools.push,
        )
    )
