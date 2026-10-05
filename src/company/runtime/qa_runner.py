from __future__ import annotations

import asyncio
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic


class QARunStatus(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class QACommandResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def passed(self) -> bool:
        return self.return_code == 0 and not self.timed_out


@dataclass
class QARun:
    run_id: str
    status: QARunStatus = QARunStatus.ACCEPTED
    results: list[QACommandResult] = field(default_factory=list)
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == QARunStatus.PASSED


class AutonomousQARunner:
    def __init__(self, timeout_seconds: float = 300.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.timeout_seconds = timeout_seconds
        self._runs: dict[str, QARun] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def get_run(self, run_id: str) -> QARun:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return self._runs[run_id]

    async def run(
        self,
        run_id: str,
        commands: Sequence[Sequence[str]],
    ) -> QARun:
        if run_id in self._runs:
            raise ValueError(f"QA run already exists: {run_id}")

        qa_run = QARun(run_id=run_id, status=QARunStatus.RUNNING)
        self._runs[run_id] = qa_run

        try:
            for command in commands:
                result = await asyncio.to_thread(
                    self._execute,
                    tuple(command),
                )
                qa_run.results.append(result)

                if not result.passed:
                    qa_run.status = (
                        QARunStatus.TIMEOUT
                        if result.timed_out
                        else QARunStatus.FAILED
                    )
                    return qa_run

            qa_run.status = QARunStatus.PASSED
            return qa_run

        except Exception as exc:
            qa_run.status = QARunStatus.FAILED
            qa_run.error = str(exc)
            return qa_run

    def start(
        self,
        run_id: str,
        commands: Sequence[Sequence[str]],
    ) -> QARun:
        if run_id in self._runs:
            raise ValueError(f"QA run already exists: {run_id}")

        qa_run = QARun(run_id=run_id, status=QARunStatus.ACCEPTED)
        self._runs[run_id] = qa_run

        task = asyncio.create_task(
            self._run_existing(qa_run, commands)
        )
        self._tasks[run_id] = task

        return qa_run

    async def wait(self, run_id: str) -> QARun:
        if run_id not in self._runs:
            raise KeyError(run_id)

        task = self._tasks.get(run_id)

        if task is not None:
            await task

        return self._runs[run_id]

    async def _run_existing(
        self,
        qa_run: QARun,
        commands: Sequence[Sequence[str]],
    ) -> None:
        qa_run.status = QARunStatus.RUNNING

        try:
            for command in commands:
                result = await asyncio.to_thread(
                    self._execute,
                    tuple(command),
                )

                qa_run.results.append(result)

                if not result.passed:
                    qa_run.status = (
                        QARunStatus.TIMEOUT
                        if result.timed_out
                        else QARunStatus.FAILED
                    )
                    return

            qa_run.status = QARunStatus.PASSED

        except Exception as exc:
            qa_run.status = QARunStatus.FAILED
            qa_run.error = str(exc)

    def _execute(
        self,
        command: tuple[str, ...],
    ) -> QACommandResult:
        started = monotonic()

        try:
            result = subprocess.run(
                list(command),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )

            return QACommandResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=monotonic() - started,
            )

        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""

            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")

            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")

            return QACommandResult(
                command=command,
                return_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=monotonic() - started,
                timed_out=True,
            )
