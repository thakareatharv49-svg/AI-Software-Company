from __future__ import annotations

from company.tools.models import (
    ToolDefinition,
    ToolRequest,
    ToolResult,
    ToolRisk,
    ToolStatus,
)


class EchoTool:
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="echo",
            description="Returns the supplied text unchanged.",
            risk=ToolRisk.READ,
            input_schema={"text": "string"},
        )

    def validate(self, arguments: dict[str, object]) -> None:
        if not isinstance(arguments.get("text"), str):
            raise ValueError("echo requires a string 'text' argument")

    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            tool_name=self.definition.name,
            output=request.arguments["text"],
        )


class AddTool:
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="add",
            description="Adds two numeric values.",
            risk=ToolRisk.READ,
            input_schema={"a": "number", "b": "number"},
        )

    def validate(self, arguments: dict[str, object]) -> None:
        if not isinstance(arguments.get("a"), (int, float)):
            raise ValueError("add requires numeric 'a'")

        if not isinstance(arguments.get("b"), (int, float)):
            raise ValueError("add requires numeric 'b'")

    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            tool_name=self.definition.name,
            output=request.arguments["a"] + request.arguments["b"],
        )
