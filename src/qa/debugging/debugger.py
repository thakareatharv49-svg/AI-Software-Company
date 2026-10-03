from collections.abc import Awaitable, Callable

from src.qa.execution.runner import QARunner
from src.qa.models.contracts import DebugAttempt, DebugResult, QATestRequest
from src.qa.models.enums import DebugStatus, QATestStatus


class AutonomousDebugger:
    def __init__(
        self,
        qa_runner: QARunner | None = None,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.qa_runner = qa_runner or QARunner()
        self.max_attempts = max_attempts

    async def run(
        self,
        request: QATestRequest,
        repair: Callable[
            [QATestRequest, str],
            Awaitable[None] | None,
        ] | None = None,
    ) -> DebugResult:
        attempts: list[DebugAttempt] = []

        for attempt_number in range(1, self.max_attempts + 1):
            result = await self.qa_runner.run(request)

            if result.status == QATestStatus.PASSED:
                return DebugResult(
                    status=(
                        DebugStatus.NOT_NEEDED
                        if attempt_number == 1
                        else DebugStatus.RESOLVED
                    ),
                    attempts=attempts,
                )

            error = result.stderr or result.stdout or "QA test failed"

            attempts.append(
                DebugAttempt(
                    attempt=attempt_number,
                    test_status=result.status,
                    error=error,
                )
            )

            if attempt_number == self.max_attempts:
                return DebugResult(
                    status=DebugStatus.BLOCKED,
                    attempts=attempts,
                    final_error=error,
                )

            if repair is not None:
                repair_result = repair(request, error)

                if repair_result is not None:
                    await repair_result

        return DebugResult(
            status=DebugStatus.BLOCKED,
            attempts=attempts,
            final_error="Debugging stopped",
        )
