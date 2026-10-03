from src.tools.builtin.registration import register_builtin_tools
from src.tools.execution.executor import ToolExecutor
from src.tools.registry.registry import ToolRegistry


def create_tool_executor(workspace: str) -> ToolExecutor:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace)
    return ToolExecutor(registry)
