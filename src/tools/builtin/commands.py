from pathlib import Path
import subprocess


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

        try:
            result = subprocess.run(
                [executable, *arguments],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Command timed out after {self.timeout_seconds} seconds"
            ) from exc

        output = result.stdout

        if result.stderr:
            output += f"\n{result.stderr}"

        output = output[: self.max_output_chars]

        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}\n{output}"
            )

        return output
