from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ToolRisk(StrEnum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    EXTERNAL = "external"


class ToolStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    risk: ToolRisk
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    actor: str = "system"


@dataclass(frozen=True)
class ToolResult:
    status: ToolStatus
    tool_name: str
    output: Any = None
    error: str | None = None


class ToolPermissionError(PermissionError):
    """Raised when a tool execution is not permitted."""
