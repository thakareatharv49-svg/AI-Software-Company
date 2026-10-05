from company.ai.audit import AIToolAuditEvent, AIToolAuditRecorder
from company.ai.tool_calling import AIToolCall, AIToolCallResponse, build_ai_tool_calling_engine


def test_audit_records_metadata() -> None:
    engine = build_ai_tool_calling_engine()

    exchanges = engine.execute_response(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "echo",
                    {"text": "secret-output"},
                ),
            )
        )
    )

    events = AIToolAuditRecorder.record_all(
        exchanges,
        actor="ai-test",
    )

    assert len(events) == 1
    assert events[0].tool_name == "echo"
    assert events[0].status == "success"
    assert events[0].actor == "ai-test"
    assert events[0].output_present is True
    assert events[0].error_present is False
    assert "secret-output" not in events[0].timestamp


def test_audit_does_not_store_output() -> None:
    engine = build_ai_tool_calling_engine()

    exchanges = engine.execute_response(
        AIToolCallResponse(
            tool_calls=(
                AIToolCall(
                    "echo",
                    {"text": "private"},
                ),
            )
        )
    )

    event = AIToolAuditRecorder.record(
        exchanges[0]
    )

    assert not hasattr(event, "output")
    assert not hasattr(event, "arguments")


def test_audit_exports_exist() -> None:
    assert AIToolAuditEvent is not None
    assert AIToolAuditRecorder is not None
