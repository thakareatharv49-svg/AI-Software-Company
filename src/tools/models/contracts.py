from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.tools.models.enums import ToolPermission


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    permission: ToolPermission
    handler: Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ToolRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResult:
    success: bool
    output: Any = None
    error: str | None = None
