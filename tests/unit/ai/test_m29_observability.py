from __future__ import annotations

from company.ai.context import AIExecutionContext
from company.ai.observability import (
    AIExecutionObservationStore,
    AIExecutionObserver,
)
from company.ai.runtime import AIExecutionRuntime
from company.ai.tool_calling import AIToolCall, AIToolCallResponse


def test_observer_records_execution() -> None:
    runtime = AIExecutionRuntime(
        __import__("company.ai.tool_calling", fromlist=["build_ai_tool_calling_engine"])
        .build_ai_tool_calling_engine()
    )

    result = runtime.execute(
        AIToolCallResponse(
            text="run",
            tool_calls=(AIToolCall("echo", {"text": "run"}),),
        ),
        context=AIExecutionContext(),
    )

    observation = AIExecutionObserver().observe(result)

    assert observation.run_id == result.run_id
    assert observation.actor == result.actor
    assert observation.rounds == 1
    assert observation.tool_calls == 1
    assert observation.success is True


def test_observation_store_records_and_reads() -> None:
    runtime = AIExecutionRuntime(
        __import__("company.ai.tool_calling", fromlist=["build_ai_tool_calling_engine"])
        .build_ai_tool_calling_engine()
    )

    result = runtime.execute(
        AIToolCallResponse(text="hello"),
        context=AIExecutionContext(),
    )

    observation = AIExecutionObserver().observe(result)
    store = AIExecutionObservationStore()
    store.record(observation)

    assert store.get(result.run_id) == observation
    assert store.list() == (observation,)


def test_observation_store_clear() -> None:
    store = AIExecutionObservationStore()
    store.clear()
    assert store.list() == ()
