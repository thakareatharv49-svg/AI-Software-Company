import os

from src.security.models.contracts import (
    PermissionDecision,
    SecurityAction,
    SecurityPolicy,
)


class PermissionDeniedError(PermissionError):
    pass


class PermissionService:
    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or SecurityPolicy(
            allow_tool_execution=os.getenv("AI_ALLOW_TOOL_EXECUTION", "true").lower()
            == "true",
            allow_github_writes=os.getenv("AI_ALLOW_GITHUB_WRITES", "false").lower()
            == "true",
            allow_shell_execution=os.getenv("AI_ALLOW_SHELL_EXECUTION", "false").lower()
            == "true",
        )

    def authorize(self, action: SecurityAction) -> PermissionDecision:
        if action in {SecurityAction.READ, SecurityAction.GITHUB_READ}:
            return PermissionDecision(
                action=action,
                allowed=True,
                reason="Read operations are allowed.",
            )

        if action is SecurityAction.TOOL_EXECUTE:
            allowed = self.policy.allow_tool_execution
            reason = (
                "Tool execution is enabled by policy."
                if allowed
                else "Tool execution is disabled by policy."
            )
        elif action is SecurityAction.GITHUB_WRITE:
            allowed = self.policy.allow_github_writes
            reason = (
                "GitHub writes are explicitly enabled by policy."
                if allowed
                else "GitHub writes require explicit permission."
            )
        elif action is SecurityAction.SHELL_EXECUTE:
            allowed = self.policy.allow_shell_execution
            reason = (
                "Shell execution is explicitly enabled by policy."
                if allowed
                else "Shell execution is disabled by default."
            )
        else:
            allowed = False
            reason = "Unknown action denied by default."

        return PermissionDecision(
            action=action,
            allowed=allowed,
            reason=reason,
        )

    def require(self, action: SecurityAction) -> None:
        decision = self.authorize(action)
        if not decision.allowed:
            raise PermissionDeniedError(decision.reason)
