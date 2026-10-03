from src.agents.models.enums import AgentPermission
from src.tools.builtin.commands import CommandTools
from src.tools.builtin.files import FileTools
from src.tools.builtin.git import GitTools
from src.tools.builtin.git_write import GitWriteTools
from src.tools.models.contracts import ToolDefinition
from src.tools.registry.registry import ToolRegistry


def register_builtin_tools(
    registry: ToolRegistry,
    workspace: str,
) -> None:
    files = FileTools(workspace)
    commands = CommandTools(workspace)
    git = GitTools(workspace)
    git_write = GitWriteTools(workspace)

    registry.register(
        ToolDefinition(
            name="read_file",
            description="Read a UTF-8 text file inside the workspace.",
            permission=AgentPermission.READ_FILES,
            handler=files.read_file,
        )
    )

    registry.register(
        ToolDefinition(
            name="write_file",
            description="Write a UTF-8 text file inside the workspace.",
            permission=AgentPermission.WRITE_FILES,
            handler=files.write_file,
        )
    )

    registry.register(
        ToolDefinition(
            name="run_command",
            description="Run an allowlisted command inside the workspace.",
            permission=AgentPermission.RUN_COMMANDS,
            handler=commands.run_command,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_status",
            description="Show Git working-tree status.",
            permission=AgentPermission.READ_FILES,
            handler=git.status,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_diff",
            description="Show the current Git diff.",
            permission=AgentPermission.READ_FILES,
            handler=git.diff,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_commit",
            description="Stage workspace changes and create a Git commit.",
            permission=AgentPermission.GIT_COMMIT,
            handler=git_write.commit,
        )
    )

    registry.register(
        ToolDefinition(
            name="git_push",
            description="Push the current Git branch to a remote.",
            permission=AgentPermission.GIT_PUSH,
            handler=git_write.push,
        )
    )
