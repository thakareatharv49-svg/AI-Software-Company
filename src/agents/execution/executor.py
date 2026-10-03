from time import perf_counter

from src.agents.execution.context import AgentExecutionContext
from src.agents.models.contracts import AgentRequest, AgentResult
from src.agents.models.enums import AgentStatus
from src.runtime.models.messages import ModelRequest
from src.runtime.service import AIRuntime


class AgentExecutor:
    def __init__(self, runtime: AIRuntime) -> None:
        self.runtime = runtime

    async def execute(
        self,
        context: AgentExecutionContext,
        request: AgentRequest,
    ) -> AgentResult:
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

        prompt = self._build_prompt(context, request)
        started = perf_counter()

        try:
            response = await self.runtime.generate(
                ModelRequest(
                    prompt=prompt,
                    system=(
                        f"You are the {context.agent.role} agent named "
                        f"{context.agent.name}. Follow the assigned instruction "
                        "and operate only within your granted permissions."
                    ),
                )
            )
        except Exception as exc:
            return AgentResult(
                task_id=request.task_id,
                agent_name=context.agent.name,
                success=False,
                error=str(exc),
                duration_ms=int((perf_counter() - started) * 1000),
            )

        return AgentResult(
            task_id=request.task_id,
            agent_name=context.agent.name,
            success=True,
            output=response.content,
            duration_ms=int((perf_counter() - started) * 1000),
        )

    @staticmethod
    def _build_prompt(
        context: AgentExecutionContext,
        request: AgentRequest,
    ) -> str:
        capabilities = ", ".join(context.agent.capabilities) or "none"
        permissions = ", ".join(
            permission.value for permission in context.allowed_permissions
        ) or "none"

        return (
            f"Task ID: {request.task_id}\n"
            f"Capabilities: {capabilities}\n"
            f"Granted permissions: {permissions}\n\n"
            f"Instruction:\n{request.instruction}\n\n"
            f"Additional context:\n{request.context}"
        )
