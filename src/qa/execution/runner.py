import time

from src.qa.models.contracts import QATestRequest, QATestResult
from src.qa.models.enums import QATestStatus
from src.sandbox import SandboxExecutor, SandboxLimits, SandboxRequest


class QARunner:
    def __init__(self, sandbox: SandboxExecutor | None = None) -> None:
        self.sandbox = sandbox or SandboxExecutor()

    async def run(self, request: QATestRequest) -> QATestResult:
        started = time.perf_counter()

        # An empty command must never count as a successful QA run.
        if not request.command or not any(part.strip() for part in request.command):
            return QATestResult(
                status=QATestStatus.FAILED,
                exit_code=2,
                stderr=(
                    "QA command is empty; refusing to mark the product as tested. "
                    "Configure an executable test or validation command."
                ),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        result = await self.sandbox.execute(
            SandboxRequest(
                command=request.command,
                working_directory=request.working_directory,
                limits=SandboxLimits(
                    timeout_seconds=request.timeout_seconds,
                ),
            )
        )

        if result.status.value == "success":
            status = QATestStatus.PASSED
        elif result.status.value == "timeout":
            status = QATestStatus.TIMEOUT
        else:
            status = QATestStatus.FAILED

        duration_ms = result.duration_ms

        if duration_ms is None:
            duration_ms = int((time.perf_counter() - started) * 1000)

        return QATestResult(
            status=status,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
        )
