from src.agents.execution.context import AgentExecutionContext
from src.tools.models.contracts import ToolRequest, ToolResult
from src.tools.registry.registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        context: AgentExecutionContext,
        request: ToolRequest,
    ) -> ToolResult:
        tool = self.registry.get(request.tool_name)

        if tool is None:
            return ToolResult(
                success=False,
                error=f"Tool '{request.tool_name}' is not registered",
            )

        if tool.permission not in context.allowed_permissions:
            return ToolResult(
                success=False,
                error=(
                    f"Agent '{context.agent.name}' does not have "
                    f"permission '{tool.permission.value}'"
                ),
            )

        try:
            output = tool.handler(**request.arguments)
        except Exception as exc:
            return ToolResult(
                success=False,
                error=str(exc),
            )

        return ToolResult(
            success=True,
            output=output,
        )
