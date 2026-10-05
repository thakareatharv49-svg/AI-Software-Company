from __future__ import annotations

from company.tools.models import ToolDefinition
from company.tools.protocol import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.definition.name.strip()

        if not name:
            raise ValueError("Tool name must not be empty")

        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")

        self._tools[name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            tool.definition
            for tool in self._tools.values()
        )

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools
