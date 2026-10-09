import pytest

from src.company.autonomous_project import AutonomousProjectRunner, StageStatus


def test_sync_stage_failure_names_stage_and_preserves_original_error() -> None:
    stages = []

    def fail():
        raise ValueError("approval service unavailable")

    with pytest.raises(RuntimeError, match="Autonomous stage 'research' failed") as error:
        AutonomousProjectRunner._run_stage(stages, "research", fail)

    assert "approval service unavailable" in str(error.value)
    assert stages[0].name == "research"
    assert stages[0].status == StageStatus.FAILED
    assert "approval service unavailable" in stages[0].detail


@pytest.mark.asyncio
async def test_async_stage_failure_names_stage_and_preserves_original_error() -> None:
    stages = []

    async def fail():
        raise TimeoutError("pipeline timed out")

    with pytest.raises(
        RuntimeError,
        match="Autonomous stage 'engineering_qa_security_github' failed",
    ) as error:
        await AutonomousProjectRunner._run_async_stage(
            stages,
            "engineering_qa_security_github",
            fail,
        )

    assert "pipeline timed out" in str(error.value)
    assert stages[0].status == StageStatus.FAILED
    assert "pipeline timed out" in stages[0].detail
