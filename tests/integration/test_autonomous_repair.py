from unittest.mock import AsyncMock

import pytest

from src.agents.execution.context import AgentExecutionContext
from src.agents.execution.executor import AgentExecutor
from src.agents.models.contracts import AgentDefinition, AgentRequest
from src.agents.models.enums import AgentPermission, AgentStatus
from src.agents.registry.registry import AgentRegistry
from src.runtime.models.messages import ModelResponse


def make_agent() -> AgentDefinition:
    return AgentDefinition(
        name="test-agent",
        role="Engineering Agent",
        capabilities=["write_code", "run_tests"],
        permissions={
            AgentPermission.READ_FILES,
            AgentPermission.WRITE_FILES,
            AgentPermission.RUN_TESTS,
        },
    )


def test_registry_register_and_get() -> None:
    registry = AgentRegistry()
    agent = make_agent()

    registry.register(agent)

    assert registry.get("test-agent") == agent
    assert len(registry.list_agents()) == 1


def test_registry_rejects_duplicate_agent() -> None:
    registry = AgentRegistry()
    agent = make_agent()

    registry.register(agent)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(agent)


def test_execution_context_enforces_permissions() -> None:
    agent = make_agent()
    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset({AgentPermission.READ_FILES}),
    )

    assert context.can(AgentPermission.READ_FILES)
    assert not context.can(AgentPermission.WRITE_FILES)

    with pytest.raises(PermissionError):
        context.require(AgentPermission.WRITE_FILES)


@pytest.mark.asyncio
async def test_executor_delegates_to_runtime() -> None:
    runtime = AsyncMock()
    runtime.generate.return_value = ModelResponse(
        content="implemented",
        model="test-model",
        provider="test",
    )

    agent = make_agent()
    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset(agent.permissions),
    )

    result = await AgentExecutor(runtime).execute(
        context,
        AgentRequest(
            task_id="task-1",
            instruction="Implement the feature.",
            context={"language": "python"},
        ),
    )

    assert result.success
    assert result.output == "implemented"
    assert result.task_id == "task-1"
    assert result.agent_name == "test-agent"
    runtime.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_executor_rejects_empty_instruction() -> None:
    runtime = AsyncMock()
    agent = make_agent()
    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset(agent.permissions),
    )

    result = await AgentExecutor(runtime).execute(
        context,
        AgentRequest(task_id="task-2", instruction="   "),
    )

    assert not result.success
    assert result.error == "Instruction cannot be empty"
    runtime.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_executor_rejects_disabled_agent() -> None:
    runtime = AsyncMock()
    agent = make_agent()
    agent.status = AgentStatus.DISABLED

    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset(agent.permissions),
    )

    result = await AgentExecutor(runtime).execute(
        context,
        AgentRequest(task_id="task-3", instruction="Do something."),
    )

    assert not result.success
    assert "not available" in result.error
    runtime.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_executor_executes_structured_tool_calls() -> None:
    runtime = AsyncMock()
    runtime.generate.return_value = ModelResponse(
        content='{"tool_calls":[{"tool_name":"read_file","arguments":{"path":"test.txt"}}]}',
        model="test-model",
        provider="test",
    )

    class FakeToolResult:
        success = True
        output = "file-content"
        error = None

    class FakeToolExecutor:
        def __init__(self):
            self.calls = []

        def execute(self, context, request):
            self.calls.append(request)
            return FakeToolResult()

    tool_executor = FakeToolExecutor()
    agent = make_agent()

    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset(agent.permissions),
    )

    result = await AgentExecutor(
        runtime,
        tool_executor=tool_executor,
    ).execute(
        context,
        AgentRequest(
            task_id="repair-1",
            instruction="Repair the failing code.",
        ),
    )

    assert result.success
    assert result.output == "file-content"
    assert len(tool_executor.calls) == 1
    assert tool_executor.calls[0].tool_name == "read_file"
