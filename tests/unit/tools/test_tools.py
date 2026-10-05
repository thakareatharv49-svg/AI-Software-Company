from company.tools import (
    AddTool,
    EchoTool,
    ToolDefinition,
    ToolExecutor,
    ToolPermissionEngine,
    ToolPermissionPolicy,
    ToolRegistry,
    ToolRequest,
    ToolRisk,
    ToolStatus,
)


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTool())
    registry.register(AddTool())
    return registry


def test_tool_registry_registers_and_lists_tools() -> None:
    registry = build_registry()
    assert registry.names() == ("echo", "add")
    assert "echo" in registry
    assert "add" in registry


def test_registry_rejects_duplicate_tools() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    try:
        registry.register(EchoTool())
        raise AssertionError("Expected duplicate registration to fail")
    except ValueError as exc:
        assert "already registered" in str(exc)


def test_tool_executor_runs_authorized_tool() -> None:
    executor = ToolExecutor(build_registry())

    result = executor.execute(
        ToolRequest(
            tool_name="echo",
            arguments={"text": "hello"},
        )
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.output == "hello"


def test_add_tool_is_deterministic() -> None:
    executor = ToolExecutor(build_registry())

    result = executor.execute(
        ToolRequest(
            tool_name="add",
            arguments={"a": 10, "b": 32},
        )
    )

    assert result.status == ToolStatus.SUCCESS
    assert result.output == 42


def test_unknown_tool_returns_failure() -> None:
    executor = ToolExecutor(build_registry())

    result = executor.execute(
        ToolRequest(tool_name="missing")
    )

    assert result.status == ToolStatus.FAILURE
    assert result.error is not None


def test_permission_engine_denies_write_risk() -> None:
    definition = ToolDefinition(
        name="dangerous",
        description="test",
        risk=ToolRisk.WRITE,
    )

    engine = ToolPermissionEngine(
        ToolPermissionPolicy(
            allowed_risks=frozenset({ToolRisk.READ})
        )
    )

    try:
        engine.authorize(
            definition,
            ToolRequest(tool_name="dangerous"),
        )
        raise AssertionError("Expected permission denial")
    except PermissionError:
        pass


def test_permission_engine_allows_explicit_tool() -> None:
    definition = ToolDefinition(
        name="approved-write",
        description="test",
        risk=ToolRisk.WRITE,
    )

    engine = ToolPermissionEngine(
        ToolPermissionPolicy(
            allowed_risks=frozenset({ToolRisk.READ}),
            allowed_tools=frozenset({"approved-write"}),
        )
    )

    engine.authorize(
        definition,
        ToolRequest(tool_name="approved-write"),
    )


def test_permission_engine_deny_list_wins() -> None:
    definition = ToolDefinition(
        name="echo",
        description="test",
        risk=ToolRisk.READ,
    )

    engine = ToolPermissionEngine(
        ToolPermissionPolicy(
            allowed_risks=frozenset({ToolRisk.READ}),
            deny_tools=frozenset({"echo"}),
        )
    )

    try:
        engine.authorize(
            definition,
            ToolRequest(tool_name="echo"),
        )
        raise AssertionError("Denied tool should not execute")
    except PermissionError:
        pass


def test_executor_returns_denied_result() -> None:
    executor = ToolExecutor(
        build_registry(),
        ToolPermissionEngine(
            ToolPermissionPolicy(allowed_risks=frozenset())
        ),
    )

    result = executor.execute(
        ToolRequest(
            tool_name="echo",
            arguments={"text": "blocked"},
        )
    )

    assert result.status == ToolStatus.DENIED
    assert result.output is None
    assert result.error is not None


def test_invalid_arguments_return_failure() -> None:
    executor = ToolExecutor(build_registry())

    result = executor.execute(
        ToolRequest(
            tool_name="add",
            arguments={"a": 10},
        )
    )

    assert result.status == ToolStatus.FAILURE
    assert result.error is not None


def test_tool_definition_is_provider_independent() -> None:
    definition = ToolDefinition(
        name="example",
        description="provider-independent tool",
        risk=ToolRisk.READ,
    )

    assert definition.name == "example"
    assert definition.risk == ToolRisk.READ
