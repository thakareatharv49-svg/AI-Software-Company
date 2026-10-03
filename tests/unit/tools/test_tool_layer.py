import subprocess
from pathlib import Path

import pytest

from src.agents.execution.context import AgentExecutionContext
from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission, AgentStatus
from src.tools.builtin.commands import CommandTools
from src.tools.builtin.files import FileTools
from src.tools.builtin.git import GitTools
from src.tools.builtin.git_write import GitWriteTools
from src.tools.builtin.registration import register_builtin_tools
from src.tools.execution.executor import ToolExecutor
from src.tools.factory import create_tool_executor
from src.tools.models.contracts import ToolDefinition, ToolRequest
from src.tools.registry.registry import ToolRegistry


def make_context(
    *permissions: AgentPermission,
) -> AgentExecutionContext:
    agent = AgentDefinition(
        name="test-agent",
        role="engineer",
        capabilities=("engineering",),
        permissions=frozenset(permissions),
        status=AgentStatus.AVAILABLE,
    )

    return AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset(permissions),
    )


def init_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
    )

    subprocess.run(
        ["git", "config", "user.name", "Test Agent"],
        cwd=path,
        check=True,
    )


def test_registry_registers_tools() -> None:
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo",
            permission=AgentPermission.READ_FILES,
            handler=lambda value: value,
        )
    )

    assert registry.get("echo") is not None
    assert len(registry.list_tools()) == 1


def test_registry_rejects_duplicate_tools() -> None:
    registry = ToolRegistry()

    tool = ToolDefinition(
        name="echo",
        description="Echo",
        permission=AgentPermission.READ_FILES,
        handler=lambda: "ok",
    )

    registry.register(tool)

    with pytest.raises(ValueError):
        registry.register(tool)


def test_tool_executor_allows_permission() -> None:
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo",
            permission=AgentPermission.READ_FILES,
            handler=lambda value: value,
        )
    )

    executor = ToolExecutor(registry)

    result = executor.execute(
        make_context(AgentPermission.READ_FILES),
        ToolRequest(
            tool_name="echo",
            arguments={"value": "hello"},
        ),
    )

    assert result.success
    assert result.output == "hello"


def test_tool_executor_blocks_permission() -> None:
    registry = ToolRegistry()

    registry.register(
        ToolDefinition(
            name="push",
            description="Push",
            permission=AgentPermission.GIT_PUSH,
            handler=lambda: "pushed",
        )
    )

    executor = ToolExecutor(registry)

    result = executor.execute(
        make_context(AgentPermission.READ_FILES),
        ToolRequest(tool_name="push"),
    )

    assert not result.success
    assert "git_push" in result.error


def test_file_tools_write_and_read(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)

    tools.write_file("hello.txt", "hello world")

    assert tools.read_file("hello.txt") == "hello world"


def test_file_tools_reject_path_escape(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)

    with pytest.raises(PermissionError):
        tools.read_file("../outside.txt")


def test_command_tool_allows_python(tmp_path: Path) -> None:
    tools = CommandTools(tmp_path)

    output = tools.run_command(
        "python",
        ["-c", "print('hello')"],
    )

    assert "hello" in output


def test_command_tool_blocks_shell(tmp_path: Path) -> None:
    tools = CommandTools(tmp_path)

    with pytest.raises(PermissionError):
        tools.run_command(
            "powershell",
            ["-Command", "Write-Output hello"],
        )


def test_command_tool_timeout(tmp_path: Path) -> None:
    tools = CommandTools(
        tmp_path,
        timeout_seconds=1,
    )

    with pytest.raises(TimeoutError):
        tools.run_command(
            "python",
            ["-c", "import time; time.sleep(3)"],
        )


def test_git_status(tmp_path: Path) -> None:
    init_repo(tmp_path)

    tools = GitTools(tmp_path)

    assert tools.status() == ""


def test_git_commit(tmp_path: Path) -> None:
    init_repo(tmp_path)

    (tmp_path / "hello.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    tools = GitWriteTools(tmp_path)

    output = tools.commit("test commit")

    assert "test commit" in output


def test_empty_git_commit_rejected(tmp_path: Path) -> None:
    init_repo(tmp_path)

    tools = GitWriteTools(tmp_path)

    with pytest.raises(ValueError):
        tools.commit("")


def test_builtin_registry_contains_all_tools(tmp_path: Path) -> None:
    registry = ToolRegistry()

    register_builtin_tools(
        registry,
        str(tmp_path),
    )

    names = {
        tool.name
        for tool in registry.list_tools()
    }

    assert names == {
        "read_file",
        "write_file",
        "run_command",
        "git_status",
        "git_diff",
        "git_commit",
        "git_push",
    }


def test_tool_factory_creates_executor(tmp_path: Path) -> None:
    executor = create_tool_executor(str(tmp_path))

    assert len(executor.registry.list_tools()) == 7

