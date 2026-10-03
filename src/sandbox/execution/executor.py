import asyncio
import time
from pathlib import Path

from src.sandbox.models.contracts import SandboxRequest, SandboxResult
from src.sandbox.models.enums import SandboxStatus


class SandboxExecutor:
    ALLOWED_COMMANDS = {
        "python",
        "python.exe",
        "pytest",
        "pytest.exe",
    }

    def __init__(self, allowed_commands: set[str] | None = None) -> None:
        self.allowed_commands = allowed_commands or self.ALLOWED_COMMANDS

    def _validate(self, request: SandboxRequest) -> None:
        if not request.command:
            raise ValueError("Sandbox command cannot be empty")

        executable = Path(request.command[0]).name.lower()

        if executable not in {
            command.lower() for command in self.allowed_commands
        }:
            raise PermissionError(
                f"Command '{request.command[0]}' is not allowed in sandbox"
            )

        working_directory = Path(request.working_directory)

        if not working_directory.exists():
            raise FileNotFoundError(
                f"Working directory does not exist: {working_directory}"
            )

        if not working_directory.is_dir():
            raise NotADirectoryError(
                f"Working directory is not a directory: {working_directory}"
            )

    async def execute(self, request: SandboxRequest) -> SandboxResult:
        self._validate(request)

        started = time.perf_counter()

        process = await asyncio.create_subprocess_exec(
            *request.command,
            cwd=request.working_directory,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=request.limits.timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            await process.wait()

            duration_ms = int((time.perf_counter() - started) * 1000)

            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                duration_ms=duration_ms,
                error="Sandbox command timed out",
            )

        duration_ms = int((time.perf_counter() - started) * 1000)

        stdout = stdout_bytes[: request.limits.max_output_bytes].decode(
            "utf-8",
            errors="replace",
        )
        stderr = stderr_bytes[: request.limits.max_output_bytes].decode(
            "utf-8",
            errors="replace",
        )

        status = (
            SandboxStatus.SUCCESS
            if process.returncode == 0
            else SandboxStatus.FAILED
        )

        return SandboxResult(
            status=status,
            exit_code=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
