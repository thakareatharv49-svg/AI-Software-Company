from __future__ import annotations

from company.ai.context import (
    AIExecutionContext,
    AIExecutionContextFactory,
)


def test_context_defaults() -> None:
    context = AIExecutionContext()

    assert context.run_id
    assert context.actor == "ai"
    assert context.max_tool_calls == 10
    assert context.max_rounds == 5


def test_context_isolates_metadata() -> None:
    source = {"project": "test"}

    context = AIExecutionContext(metadata=source)

    source["changed"] = True

    assert context.metadata == {"project": "test"}


def test_context_factory() -> None:
    context = AIExecutionContextFactory.create(
        actor="agent",
        metadata={"mission": "build"},
        max_tool_calls=4,
        max_rounds=2,
    )

    assert context.actor == "agent"
    assert context.metadata == {"mission": "build"}
    assert context.max_tool_calls == 4
    assert context.max_rounds == 2


def test_invalid_limits_are_rejected() -> None:
    try:
        AIExecutionContext(max_tool_calls=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative tool-call limit was accepted")

    try:
        AIExecutionContext(max_rounds=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative round limit was accepted")


def test_context_exports() -> None:
    assert AIExecutionContext is not None
    assert AIExecutionContextFactory is not None
