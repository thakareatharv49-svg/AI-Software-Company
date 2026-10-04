import sys

import pytest

from company.runtime.qa_runner import (
    AutonomousQARunner,
    QARunStatus,
)


def python_command(code: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code)


@pytest.mark.asyncio
async def test_passes_all_commands():
    runner = AutonomousQARunner(timeout_seconds=5)

    result = await runner.run(
        "qa-pass",
        [
            python_command("print('first')"),
            python_command("print('second')"),
        ],
    )

    assert result.status == QARunStatus.PASSED
    assert result.passed
    assert len(result.results) == 2
    assert result.results[0].stdout.strip() == "first"


@pytest.mark.asyncio
async def test_stops_after_failure():
    runner = AutonomousQARunner(timeout_seconds=5)

    result = await runner.run(
        "qa-failure",
        [
            python_command("print('before')"),
            python_command("import sys; sys.exit(4)"),
            python_command("raise RuntimeError('should not run')"),
        ],
    )

    assert result.status == QARunStatus.FAILED
    assert not result.passed
    assert len(result.results) == 2
    assert result.results[-1].return_code == 4


@pytest.mark.asyncio
async def test_timeout():
    runner = AutonomousQARunner(timeout_seconds=0.1)

    result = await runner.run(
        "qa-timeout",
        [
            python_command("import time; time.sleep(1)"),
        ],
    )

    assert result.status == QARunStatus.TIMEOUT
    assert result.results[0].timed_out


@pytest.mark.asyncio
async def test_captures_stderr():
    runner = AutonomousQARunner(timeout_seconds=5)

    result = await runner.run(
        "qa-stderr",
        [
            python_command(
                "import sys; "
                "sys.stderr.write('failure details'); "
                "sys.exit(2)"
            ),
        ],
    )

    assert result.status == QARunStatus.FAILED
    assert "failure details" in result.results[0].stderr


@pytest.mark.asyncio
async def test_unknown_run():
    runner = AutonomousQARunner()

    with pytest.raises(KeyError):
        await runner.wait("missing")


@pytest.mark.asyncio
async def test_background_execution():
    runner = AutonomousQARunner(timeout_seconds=5)

    accepted = runner.start(
        "qa-background",
        [
            python_command("print('background')"),
        ],
    )

    assert accepted.status == QARunStatus.ACCEPTED

    result = await runner.wait("qa-background")

    assert result.status == QARunStatus.PASSED
    assert result.results[0].stdout.strip() == "background"


def test_invalid_timeout():
    with pytest.raises(ValueError):
        AutonomousQARunner(timeout_seconds=0)


@pytest.mark.asyncio
async def test_duplicate_run_rejected():
    runner = AutonomousQARunner(timeout_seconds=5)

    await runner.run(
        "duplicate",
        [python_command("print('ok')")],
    )

    with pytest.raises(ValueError):
        await runner.run(
            "duplicate",
            [python_command("print('again')")],
        )
