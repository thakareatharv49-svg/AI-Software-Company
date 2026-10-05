from __future__ import annotations

from company.tools.models import (
    ToolRequest,
    ToolResult,
    ToolStatus,
)
from company.tools.permissions import ToolPermissionEngine
from company.tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        permission_engine: ToolPermissionEngine | None = None,
    ) -> None:
        self.registry = registry
        self.permission_engine = (
            permission_engine or ToolPermissionEngine()
        )

    def execute(self, request: ToolRequest) -> ToolResult:
        try:
            tool = self.registry.get(request.tool_name)
        except KeyError as exc:
            return ToolResult(
                status=ToolStatus.FAILURE,
                tool_name=request.tool_name,
                error=str(exc),
            )

        try:
            self.permission_engine.authorize(
                tool.definition,
                request,
            )
        except PermissionError as exc:
            return ToolResult(
                status=ToolStatus.DENIED,
                tool_name=request.tool_name,
                error=str(exc),
            )

        try:
            tool.validate(request.arguments)
            return tool.execute(request)
        except Exception as exc:
            return ToolResult(
                status=ToolStatus.FAILURE,
                tool_name=request.tool_name,
                error=str(exc),
            )
