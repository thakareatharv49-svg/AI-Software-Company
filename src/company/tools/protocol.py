from __future__ import annotations

from typing import Any, Protocol

from company.tools.models import ToolDefinition, ToolRequest, ToolResult


class Tool(Protocol):
    @property
    def definition(self) -> ToolDefinition:
        ...

    def execute(self, request: ToolRequest) -> ToolResult:
        ...

    def validate(self, arguments: dict[str, Any]) -> None:
        ...
