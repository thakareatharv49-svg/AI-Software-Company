from company.ai.aggregation import AIToolResultAggregator, AIToolSummary
from company.ai.tool_calling import AIToolCallingEngine, AIToolCallResponse


def test_aggregator_counts_success() -> None:
    engine = AIToolCallingEngine(
        __import__(
            "company.agents.tool_integration",
            fromlist=["build_safe_agent_tool_runner"],
        ).build_safe_agent_tool_runner()
    )

    exchanges = engine.execute_response(
        AIToolCallResponse(
            tool_calls=(
                __import__(
                    "company.ai.tool_calling",
                    fromlist=["AIToolCall"],
                ).AIToolCall("echo", {"text": "a"}),
                __import__(
                    "company.ai.tool_calling",
                    fromlist=["AIToolCall"],
                ).AIToolCall("add", {"a": 1, "b": 2}),
            )
        )
    )

    summary = AIToolResultAggregator.summarize(exchanges)

    assert summary.total == 2
    assert summary.successful == 2
    assert summary.failed == 0
    assert summary.denied == 0
    assert summary.outputs == ("a", 3)


def test_aggregator_counts_failure() -> None:
    engine = AIToolCallingEngine(
        __import__(
            "company.agents.tool_integration",
            fromlist=["build_safe_agent_tool_runner"],
        ).build_safe_agent_tool_runner()
    )

    exchanges = engine.execute_response(
        AIToolCallResponse(
            tool_calls=(
                __import__(
                    "company.ai.tool_calling",
                    fromlist=["AIToolCall"],
                ).AIToolCall("unknown", {}),
            )
        )
    )

    summary = AIToolResultAggregator.summarize(exchanges)

    assert summary.total == 1
    assert summary.successful == 0
    assert summary.failed == 1


def test_aggregation_exports_exist() -> None:
    assert AIToolResultAggregator is not None
    assert AIToolSummary is not None
