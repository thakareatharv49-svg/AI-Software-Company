from pathlib import Path

import pytest

from src.qa import (
    AutonomousDebugger,
    DebugStatus,
    QARunner,
    QATestRequest,
    QATestStatus,
)


def make_request(code: str) -> QATestRequest:
    return QATestRequest(
        command=["python", "-c", code],
        working_directory=str(Path.cwd()),
    )


@pytest.mark.asyncio
async def test_qa_runner_passes():
    runner = QARunner()

    result = await runner.run(
        make_request("print('qa-ok')")
    )

    assert result.status == QATestStatus.PASSED
    assert "qa-ok" in result.stdout


@pytest.mark.asyncio
async def test_qa_runner_fails():
    runner = QARunner()

    result = await runner.run(
        make_request("raise SystemExit(1)")
    )

    assert result.status == QATestStatus.FAILED
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_debugger_does_not_retry_success():
    debugger = AutonomousDebugger(max_attempts=3)

    result = await debugger.run(
        make_request("print('success')")
    )

    assert result.status == DebugStatus.NOT_NEEDED
    assert result.attempts == []


@pytest.mark.asyncio
async def test_debugger_stops_after_bounded_retries():
    debugger = AutonomousDebugger(max_attempts=2)

    result = await debugger.run(
        make_request("raise SystemExit(1)")
    )

    assert result.status == DebugStatus.BLOCKED
    assert len(result.attempts) == 2


@pytest.mark.asyncio
async def test_debugger_resolves_after_repair():
    debugger = AutonomousDebugger(max_attempts=3)
    state = {"fixed": False}

    async def repair(request: QATestRequest, error: str) -> None:
        state["fixed"] = True
        request.command = ["python", "-c", "print('fixed')"]

    result = await debugger.run(
        make_request("raise SystemExit(1)"),
        repair=repair,
    )

    assert state["fixed"] is True
    assert result.status == DebugStatus.RESOLVED
    assert len(result.attempts) == 1
