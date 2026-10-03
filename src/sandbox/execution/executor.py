import asyncio
import os
import subprocess
import time
from pathlib import Path

from src.sandbox.models.contracts import (
    SandboxLimits,
    SandboxRequest,
    SandboxResult,
)
from src.sandbox.models.enums import SandboxStatus


class SandboxExecutor:
    ALLOWED_COMMANDS = {
        "python",
        "python.exe",
        "pytest",
        "pytest.exe",
    }

    SAFE_ENVIRONMENT_KEYS = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "HOME",
        "USERNAME",
        "USER",
        "LANG",
        "LC_ALL",
        "VIRTUAL_ENV",
    }

    def __init__(
        self,
        allowed_commands: set[str] | None = None,
        workspace: str | Path | None = None,
        default_limits: SandboxLimits | None = None,
    ) -> None:
        self.allowed_commands = (
            allowed_commands
            if allowed_commands is not None
            else self.ALLOWED_COMMANDS
        )

        self.workspace = (
            Path(workspace).resolve()
            if workspace is not None
            else None
        )

        self.default_limits = default_limits or SandboxLimits()

    def _validate(self, request: SandboxRequest) -> Path:
        if not request.command:
            raise ValueError("Sandbox command cannot be empty")

        executable = Path(request.command[0]).name.lower()

        if executable not in {
            command.lower() for command in self.allowed_commands
        }:
            raise PermissionError(
                f"Command '{request.command[0]}' is not allowed in sandbox"
            )

        working_directory = Path(request.working_directory).resolve()

        if not working_directory.exists():
            raise FileNotFoundError(
                f"Working directory does not exist: {working_directory}"
            )

        if not working_directory.is_dir():
            raise NotADirectoryError(
                f"Working directory is not a directory: {working_directory}"
            )

        if self.workspace is not None:
            try:
                working_directory.relative_to(self.workspace)
            except ValueError as exc:
                raise PermissionError(
                    "Working directory is outside the sandbox workspace"
                ) from exc

        return working_directory

    def _build_environment(self) -> dict[str, str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in self.SAFE_ENVIRONMENT_KEYS
        }

        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"

        return environment

    @staticmethod
    def _decode_output(data: bytes, max_bytes: int) -> str:
        return data[:max_bytes].decode(
            "utf-8",
            errors="replace",
        )

    async def execute(self, request: SandboxRequest) -> SandboxResult:
        working_directory = self._validate(request)

        started = time.perf_counter()

        process = await asyncio.create_subprocess_exec(
            *request.command,
            cwd=str(working_directory),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._build_environment(),
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

        stdout = self._decode_output(
            stdout_bytes,
            request.limits.max_output_bytes,
        )
        stderr = self._decode_output(
            stderr_bytes,
            request.limits.max_output_bytes,
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

    def execute_sync(self, request: SandboxRequest) -> SandboxResult:
        working_directory = self._validate(request)

        started = time.perf_counter()

        try:
            result = subprocess.run(
                request.command,
                cwd=str(working_directory),
                capture_output=True,
                timeout=request.limits.timeout_seconds,
                check=False,
                env=self._build_environment(),
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - started) * 1000)

            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                duration_ms=duration_ms,
                error="Sandbox command timed out",
            )

        duration_ms = int((time.perf_counter() - started) * 1000)

        stdout = self._decode_output(
            result.stdout or b"",
            request.limits.max_output_bytes,
        )
        stderr = self._decode_output(
            result.stderr or b"",
            request.limits.max_output_bytes,
        )

        status = (
            SandboxStatus.SUCCESS
            if result.returncode == 0
            else SandboxStatus.FAILED
        )

        return SandboxResult(
            status=status,
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
