from pathlib import Path

from src.sandbox import SandboxExecutor, SandboxLimits, SandboxRequest


class CommandTools:
    ALLOWED_COMMANDS = frozenset(
        {
            "python",
            "python.exe",
            "pytest",
            "pytest.exe",
        }
    )

    def __init__(
        self,
        workspace: str | Path,
        timeout_seconds: int = 30,
        max_output_chars: int = 20_000,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

        self.sandbox = SandboxExecutor(
            allowed_commands=set(self.ALLOWED_COMMANDS),
            workspace=self.workspace,
            default_limits=SandboxLimits(
                timeout_seconds=timeout_seconds,
                max_output_bytes=max_output_chars,
            ),
        )

    def run_command(
        self,
        command: str,
        args: list[str] | None = None,
    ) -> str:
        executable = command.strip()

        if executable not in self.ALLOWED_COMMANDS:
            raise PermissionError(
                f"Command '{executable}' is not allowed"
            )

        arguments = args or []

        result = self.sandbox.execute_sync(
            SandboxRequest(
                command=[executable, *arguments],
                working_directory=str(self.workspace),
                limits=SandboxLimits(
                    timeout_seconds=self.timeout_seconds,
                    max_output_bytes=self.max_output_chars,
                ),
            )
        )

        if result.status.value == "timeout":
            raise TimeoutError(
                f"Command timed out after {self.timeout_seconds} seconds"
            )

        output = result.stdout

        if result.stderr:
            output += f"\n{result.stderr}"

        if result.status.value != "success":
            raise RuntimeError(
                f"Command failed with exit code "
                f"{result.exit_code}\n{output}"
            )

        return output[: self.max_output_chars]
