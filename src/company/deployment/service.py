from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeploymentConfig:
    command: tuple[str, ...]
    rollback_command: tuple[str, ...] = ()
    timeout_seconds: float = 300.0
    environment: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class DeploymentResult:
    success: bool
    status: str
    message: str
    rollback_available: bool = False


@dataclass(frozen=True, slots=True)
class _CompletedProcess:
    returncode: int
    stdout: bytes
    stderr: bytes


class DeploymentService:
    """Execute a configured deployment with timeout and rollback support."""

    async def deploy(self, config: DeploymentConfig, working_directory: Path) -> DeploymentResult:
        if not config.command:
            raise ValueError("Deployment command cannot be empty")
        result = await self._run(config.command, working_directory, config)
        if result.returncode == 0:
            return DeploymentResult(
                True,
                "deployed",
                result.stdout.decode().strip() or "Deployment completed.",
                bool(config.rollback_command),
            )
        return DeploymentResult(
            False,
            "failed",
            result.stderr.decode().strip()
            or result.stdout.decode().strip()
            or "Deployment failed.",
            bool(config.rollback_command),
        )

    async def rollback(self, config: DeploymentConfig, working_directory: Path) -> DeploymentResult:
        if not config.rollback_command:
            return DeploymentResult(False, "unavailable", "No rollback command configured.")
        result = await self._run(config.rollback_command, working_directory, config)
        return DeploymentResult(
            result.returncode == 0,
            "rolled_back" if result.returncode == 0 else "rollback_failed",
            result.stdout.decode().strip()
            or result.stderr.decode().strip()
            or "Rollback completed.",
        )

    async def _run(
        self,
        command: tuple[str, ...],
        cwd: Path,
        config: DeploymentConfig,
    ) -> _CompletedProcess:
        env = os.environ.copy()
        if config.environment:
            env.update(config.environment)
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=config.timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return _CompletedProcess(124, b"", b"Deployment timed out.")
        return _CompletedProcess(process.returncode or 0, stdout, stderr)
