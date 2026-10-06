from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceConfig:
    root: Path
    timeout_seconds: float = 60.0
    max_output_bytes: int = 200_000
    max_file_bytes: int = 2_000_000
    max_artifact_bytes: int = 10_000_000
    max_artifacts: int = 100


@dataclass(frozen=True, slots=True)
class WorkspaceFile:
    path: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    truncated: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Artifact:
    path: str
    size_bytes: int
    absolute_path: Path
