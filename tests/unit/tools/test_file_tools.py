from pathlib import Path

import pytest

from src.agents.execution.context import AgentExecutionContext
from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission, AgentStatus
from src.tools.builtin.files import FileTools


def context(*permissions: AgentPermission) -> AgentExecutionContext:
    agent = AgentDefinition(
        name="test-agent",
        role="engineer",
        capabilities=("files",),
        permissions=frozenset(permissions),
        status=AgentStatus.AVAILABLE,
    )
    return AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset(permissions),
    )


def test_file_tools_write_and_read(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)

    tools.write_file("hello.txt", "hello world")

    assert tools.read_file("hello.txt") == "hello world"


def test_file_tools_reject_path_escape(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)

    with pytest.raises(PermissionError):
        tools.read_file("../outside.txt")


def test_file_tools_work_inside_workspace(tmp_path: Path) -> None:
    tools = FileTools(tmp_path)

    tools.write_file("nested/test.txt", "data")

    assert (tmp_path / "nested" / "test.txt").read_text() == "data"
