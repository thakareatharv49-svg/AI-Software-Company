from __future__ import annotations

from src.agents.execution.context import AgentExecutionContext
from src.agents.models.contracts import AgentDefinition
from src.agents.models.enums import AgentPermission
from src.security.redaction import redact_sensitive_text, redact_sensitive_value
from src.tools.execution.executor import ToolExecutor
from src.tools.models.contracts import ToolDefinition, ToolRequest
from src.tools.registry.registry import ToolRegistry


def test_redacts_bearer_password_and_database_url_secrets() -> None:
    token = "Bearer " + "A" * 32
    text = (
        "Authorization: " + token
        + " password=super-secret-password "
        + "DATABASE_URL=postgresql://service:db-password@db.internal/app"
    )
    redacted = redact_sensitive_text(text)
    assert "A" * 20 not in redacted
    assert "super-secret-password" not in redacted
    assert "db-password" not in redacted
    assert "[REDACTED]" in redacted


def test_redacts_provider_tokens_and_jwts() -> None:
    github_token = "ghp_" + "B" * 32
    jwt = ".".join(("eyJ" + "a" * 12, "eyJ" + "b" * 12, "c" * 12))
    redacted = redact_sensitive_text(f"token={github_token} session={jwt}")
    assert github_token not in redacted
    assert jwt not in redacted
    assert "[REDACTED_TOKEN]" in redacted
    assert "[REDACTED_JWT]" in redacted


def test_recursively_redacts_nested_tool_output() -> None:
    value = {
        "message": "password=top-secret-password",
        "items": ["Bearer " + "C" * 24],
        "meta": ("DATABASE_URL=postgresql://user:private-pass@db/app",),
    }
    redacted = redact_sensitive_value(value)
    assert "top-secret-password" not in str(redacted)
    assert "C" * 20 not in str(redacted)
    assert "private-pass" not in str(redacted)
    assert isinstance(redacted["items"], list)
    assert isinstance(redacted["meta"], tuple)


def test_tool_executor_redacts_exception_messages() -> None:
    secret = "ghp_" + "D" * 32
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="unsafe",
            description="test tool",
            permission=AgentPermission.READ_FILES,
            handler=lambda: (_ for _ in ()).throw(
                RuntimeError("request failed with token " + secret)
            ),
        )
    )
    agent = AgentDefinition(
        name="builder",
        role="software engineer",
        permissions={AgentPermission.READ_FILES},
    )
    context = AgentExecutionContext(
        agent=agent,
        allowed_permissions=frozenset({AgentPermission.READ_FILES}),
    )
    result = ToolExecutor(registry).execute(context, ToolRequest(tool_name="unsafe"))
    assert result.success is False
    assert secret not in (result.error or "")
    assert "[REDACTED_TOKEN]" in (result.error or "")
