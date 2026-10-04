
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path


class RuntimeSecurityError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeSecurityPolicy:
    allowed_commands: tuple[str, ...] = (
        "python",
        "python3",
        "pytest",
        "ruff",
        "git",
        "gh",
    )
    blocked_env_keys: tuple[str, ...] = (
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
    )
    allowed_working_directory: str | None = None
    max_command_length: int = 4096
    allow_shell: bool = False


@dataclass
class RuntimeSecurityGuard:
    policy: RuntimeSecurityPolicy = field(default_factory=RuntimeSecurityPolicy)

    def validate_command(self, command: str | list[str]) -> list[str]:
        if isinstance(command, str):
            if not self.policy.allow_shell:
                parts = shlex.split(command)
            else:
                parts = [command]
        else:
            parts = list(command)

        if not parts:
            raise RuntimeSecurityError("empty command")

        if len(" ".join(parts)) > self.policy.max_command_length:
            raise RuntimeSecurityError("command exceeds maximum length")

        executable = Path(parts[0]).name.lower()
        allowed = {Path(item).name.lower() for item in self.policy.allowed_commands}

        if executable not in allowed:
            raise RuntimeSecurityError(
                f"command not allowed: {executable}"
            )

        if any("\x00" in part for part in parts):
            raise RuntimeSecurityError("null byte detected")

        return parts

    def validate_working_directory(self, working_directory: str | Path | None) -> Path | None:
        if working_directory is None:
            return None

        path = Path(working_directory).resolve()

        if self.policy.allowed_working_directory is not None:
            root = Path(self.policy.allowed_working_directory).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise RuntimeSecurityError(
                    "working directory is outside the allowed runtime directory"
                ) from exc

        if not path.exists():
            raise RuntimeSecurityError("working directory does not exist")

        if not path.is_dir():
            raise RuntimeSecurityError("working directory is not a directory")

        return path

    def sanitize_environment(
        self,
        environment: dict[str, str] | None = None,
    ) -> dict[str, str]:
        source = dict(os.environ if environment is None else environment)
        blocked = {key.upper() for key in self.policy.blocked_env_keys}

        return {
            key: value
            for key, value in source.items()
            if key.upper() not in blocked
        }

    def validate_environment(self, environment: dict[str, str]) -> None:
        blocked = {key.upper() for key in self.policy.blocked_env_keys}

        leaked = [key for key in environment if key.upper() in blocked]

        if leaked:
            raise RuntimeSecurityError(
                f"sensitive environment variables detected: {', '.join(sorted(leaked))}"
            )


def create_runtime_security_guard(
    allowed_working_directory: str | None = None,
) -> RuntimeSecurityGuard:
    policy = RuntimeSecurityPolicy(
        allowed_working_directory=allowed_working_directory
    )
    return RuntimeSecurityGuard(policy=policy)
