from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

from src.sandbox.execution.executor import SandboxExecutor
from src.sandbox.models.contracts import SandboxLimits, SandboxRequest
from src.sandbox.models.enums import SandboxStatus

from .models import Artifact, CommandResult, WorkspaceFile


class ProjectWorkspace:
    """Isolated project workspace using the existing sandbox executor."""

    def __init__(
        self,
        root: Path,
        *,
        timeout_seconds: float = 60.0,
        max_output_bytes: int = 200_000,
        max_file_bytes: int = 2_000_000,
        max_artifact_bytes: int = 10_000_000,
        max_artifacts: int = 100,
    ) -> None:
        self.root = root.resolve()
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.max_file_bytes = max_file_bytes
        self.max_artifact_bytes = max_artifact_bytes
        self.max_artifacts = max_artifacts

        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create(
        cls,
        workspace_root: Path | str,
        project_id: str,
        **limits: object,
    ) -> ProjectWorkspace:
        parent = Path(workspace_root).resolve()
        parent.mkdir(parents=True, exist_ok=True)

        safe_id = re.sub(
            r"[^A-Za-z0-9_-]",
            "-",
            project_id,
        ).strip("-")

        safe_id = safe_id or "project"

        root = Path(
            tempfile.mkdtemp(
                prefix=f"{safe_id}-",
                dir=parent,
            )
        )

        return cls(root, **limits)

    def _resolve(self, relative_path: str | Path) -> Path:
        candidate = Path(relative_path)

        if candidate.is_absolute():
            raise ValueError("absolute paths are not allowed")

        resolved = (self.root / candidate).resolve()

        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("path escapes workspace") from exc

        return resolved

    def write_file(
        self,
        path: str | Path,
        content: str | bytes,
    ) -> WorkspaceFile:
        target = self._resolve(path)

        data = (
            content.encode("utf-8")
            if isinstance(content, str)
            else content
        )

        if len(data) > self.max_file_bytes:
            raise ValueError(
                "file exceeds workspace file-size limit"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

        return WorkspaceFile(
            path=target.relative_to(self.root).as_posix(),
            size_bytes=len(data),
        )

    def read_file(self, path: str | Path) -> str:
        target = self._resolve(path)

        if not target.is_file():
            raise FileNotFoundError(path)

        if target.stat().st_size > self.max_file_bytes:
            raise ValueError(
                "file exceeds workspace file-size limit"
            )

        return target.read_text(encoding="utf-8")

    def delete_file(self, path: str | Path) -> None:
        target = self._resolve(path)

        if not target.exists():
            return

        if target.is_dir():
            raise IsADirectoryError(path)

        target.unlink()

    def list_files(self) -> tuple[WorkspaceFile, ...]:
        files: list[WorkspaceFile] = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            files.append(
                WorkspaceFile(
                    path=path.relative_to(self.root).as_posix(),
                    size_bytes=path.stat().st_size,
                )
            )

        return tuple(
            sorted(
                files,
                key=lambda item: item.path,
            )
        )

    def _command_request(
        self,
        command: list[str] | tuple[str, ...],
    ) -> SandboxRequest:
        if not command:
            raise ValueError("command cannot be empty")

        return SandboxRequest(
            command=list(command),
            working_directory=str(self.root),
            limits=SandboxLimits(
                timeout_seconds=self.timeout_seconds,
                max_output_bytes=self.max_output_bytes,
            ),
        )

    def _executor(self) -> SandboxExecutor:
        return SandboxExecutor(
            workspace=self.root,
        )

    @staticmethod
    def _convert_result(
        command: list[str] | tuple[str, ...],
        result: object,
    ) -> CommandResult:
        status = result.status

        return CommandResult(
            command=tuple(command),
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms or 0,
            timed_out=status == SandboxStatus.TIMEOUT,
            error=result.error,
        )

    async def execute(
        self,
        command: list[str] | tuple[str, ...],
    ) -> CommandResult:
        request = self._command_request(command)
        result = await self._executor().execute(request)

        return self._convert_result(command, result)

    def execute_sync(
        self,
        command: list[str] | tuple[str, ...],
    ) -> CommandResult:
        request = self._command_request(command)
        result = self._executor().execute_sync(request)

        return self._convert_result(command, result)

    async def test(
        self,
        command: list[str] | tuple[str, ...] | None = None,
    ) -> CommandResult:
        if command is None:
            command = (
                sys.executable,
                "-m",
                "pytest",
                "-q",
            )

        return await self.execute(command)

    async def build(
        self,
        command: list[str] | tuple[str, ...] | None = None,
    ) -> CommandResult:
        if command is None:
            command = (
                sys.executable,
                "-m",
                "compileall",
                "-q",
                ".",
            )

        return await self.execute(command)

    def collect_artifacts(
        self,
        patterns: tuple[str, ...] = (
            "dist/**",
            "build/**",
            "*.whl",
        ),
    ) -> tuple[Artifact, ...]:
        artifacts: dict[str, Artifact] = {}

        for pattern in patterns:
            for path in self.root.glob(pattern):
                if not path.is_file():
                    continue

                relative = path.relative_to(
                    self.root
                ).as_posix()

                if relative in artifacts:
                    continue

                if len(artifacts) >= self.max_artifacts:
                    raise ValueError(
                        "artifact count limit exceeded"
                    )

                size = path.stat().st_size

                if size > self.max_artifact_bytes:
                    raise ValueError(
                        f"artifact exceeds size limit: {relative}"
                    )

                artifacts[relative] = Artifact(
                    path=relative,
                    size_bytes=size,
                    absolute_path=path,
                )

        return tuple(
            artifacts[path]
            for path in sorted(artifacts)
        )

    def destroy(self) -> None:
        shutil.rmtree(
            self.root,
            ignore_errors=True,
        )


