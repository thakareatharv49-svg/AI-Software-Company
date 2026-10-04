import pytest

from src.company.runtime import (
    RuntimeAlertingExecutor,
    RuntimeAlertManager,
)


@pytest.mark.asyncio
async def test_alert_is_created_above_threshold() -> None:
    manager = RuntimeAlertManager()

    alert = await manager.check(
        metric="failures",
        value=3,
        threshold=2,
        message="too many failures",
    )

    assert alert is not None
    assert alert.level == "warning"
    assert alert.metric == "failures"
    assert alert.value == 3
    assert alert.threshold == 2


@pytest.mark.asyncio
async def test_no_alert_when_value_is_within_threshold() -> None:
    manager = RuntimeAlertManager()

    alert = await manager.check(
        metric="failures",
        value=2,
        threshold=2,
        message="normal",
    )

    assert alert is None
    assert await manager.alerts() == []


@pytest.mark.asyncio
async def test_alerts_are_stored() -> None:
    manager = RuntimeAlertManager()

    await manager.check(
        metric="failures",
        value=3,
        threshold=2,
        message="first",
    )

    await manager.check(
        metric="active_tasks",
        value=5,
        threshold=4,
        message="second",
    )

    alerts = await manager.alerts()

    assert len(alerts) == 2
    assert alerts[0].message == "first"
    assert alerts[1].message == "second"


@pytest.mark.asyncio
async def test_alerts_can_be_cleared() -> None:
    manager = RuntimeAlertManager()

    await manager.check(
        metric="failures",
        value=1,
        threshold=0,
        message="failure",
    )

    await manager.clear()

    assert await manager.alerts() == []


@pytest.mark.asyncio
async def test_invalid_threshold_is_rejected() -> None:
    manager = RuntimeAlertManager()

    with pytest.raises(ValueError, match="threshold"):
        await manager.check(
            metric="failures",
            value=1,
            threshold=-1,
            message="invalid",
        )


@pytest.mark.asyncio
async def test_executor_creates_failure_alert() -> None:
    manager = RuntimeAlertManager()

    async def operation() -> None:
        raise RuntimeError("execution failed")

    executor = RuntimeAlertingExecutor(operation, manager)

    with pytest.raises(RuntimeError, match="execution failed"):
        await executor.execute()

    alerts = await manager.alerts()

    assert len(alerts) == 1
    assert alerts[0].level == "error"
    assert alerts[0].metric == "execution_failures"
    assert alerts[0].value == 1


@pytest.mark.asyncio
async def test_executor_does_not_alert_success() -> None:
    manager = RuntimeAlertManager()

    async def operation() -> str:
        return "success"

    executor = RuntimeAlertingExecutor(operation, manager)

    assert await executor.execute() == "success"
    assert await manager.alerts() == []
