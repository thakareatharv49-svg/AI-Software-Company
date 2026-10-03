from time import perf_counter

from src.agents.execution.context import AgentExecutionContext
from src.agents.models.contracts import AgentRequest, AgentResult
from src.agents.models.enums import AgentStatus
from src.runtime.models.messages import ModelRequest
from src.runtime.service import AIRuntime
from src.tools.execution.executor import ToolExecutor
from src.tools.models.contracts import ToolRequest


class AgentExecutor:
    def __init__(
        self,
        runtime: AIRuntime,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        self.runtime = runtime
        self.tool_executor = tool_executor

    async def execute(
        self,
        context: AgentExecutionContext,
        request: AgentRequest,
    ) -> AgentResult:
        started = perf_counter()

        if context.agent.status != AgentStatus.AVAILABLE:
            return AgentResult(
                task_id=request.task_id,
                agent_name=context.agent.name,
                success=False,
                error=f"Agent '{context.agent.name}' is not available",
            )

        instruction = request.instruction.strip()

        if not instruction:
            return AgentResult(
                task_id=request.task_id,
                agent_name=context.agent.name,
                success=False,
                error="Instruction cannot be empty",
            )

        tool_result = self._execute_requested_tool(
            context,
            request,
        )

        if tool_result is not None:
            if not tool_result.success:
                return AgentResult(
                    task_id=request.task_id,
                    agent_name=context.agent.name,
                    success=False,
                    error=tool_result.error,
                    duration_ms=int(
                        (perf_counter() - started) * 1000
                    ),
                )

            return AgentResult(
                task_id=request.task_id,
                agent_name=context.agent.name,
                success=True,
                output=str(tool_result.output),
                duration_ms=int(
                    (perf_counter() - started) * 1000
                ),
            )

        prompt = self._build_prompt(context, request)

        try:
            response = await self.runtime.generate(
                ModelRequest(
                    prompt=prompt,
                    system=(
                        f"You are the {context.agent.role} agent named "
                        f"{context.agent.name}. Follow the assigned "
                        "instruction and operate only within your "
                        "granted permissions."
                    ),
                )
            )
        except Exception as exc:
            return AgentResult(
                task_id=request.task_id,
                agent_name=context.agent.name,
                success=False,
                error=str(exc),
                duration_ms=int(
                    (perf_counter() - started) * 1000
                ),
            )

        return AgentResult(
            task_id=request.task_id,
            agent_name=context.agent.name,
            success=True,
            output=response.content,
            duration_ms=int(
                (perf_counter() - started) * 1000
            ),
        )

    def _execute_requested_tool(
        self,
        context: AgentExecutionContext,
        request: AgentRequest,
    ):
        if self.tool_executor is None:
            return None

        tool_name = request.context.get("tool_name")

        if not tool_name:
            return None

        arguments = request.context.get(
            "tool_arguments",
            {},
        )

        return self.tool_executor.execute(
            context,
            ToolRequest(
                tool_name=tool_name,
                arguments=arguments,
            ),
        )

    @staticmethod
    def _build_prompt(
        context: AgentExecutionContext,
        request: AgentRequest,
    ) -> str:
        capabilities = ", ".join(
            context.agent.capabilities
        ) or "none"

        permissions = ", ".join(
            permission.value
            for permission in context.allowed_permissions
        ) or "none"

        return (
            f"Task ID: {request.task_id}\n"
            f"Capabilities: {capabilities}\n"
            f"Granted permissions: {permissions}\n\n"
            f"Instruction:\n{request.instruction}\n\n"
            f"Additional context:\n{request.context}"
        )
