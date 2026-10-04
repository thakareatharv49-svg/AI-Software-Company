from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from company.runtime.deadlines import (
    RuntimeDeadline,
    RuntimeDeadlineController,
)


def test_deadline_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        RuntimeDeadline(datetime.now())


def test_deadline_rejects_negative_duration() -> None:
    with pytest.raises(ValueError):
        RuntimeDeadline.after(-1)


def test_deadline_reports_remaining_time() -> None:
    deadline = RuntimeDeadline.after(1)

    assert deadline.remaining_seconds() > 0
    assert deadline.expired() is False


@pytest.mark.asyncio
async def test_deadline_allows_fast_operation() -> None:
    controller = RuntimeDeadlineController(RuntimeDeadline.after(1))

    async def operation():
        await asyncio.sleep(0.01)

    result = await controller.execute(operation)

    assert result.completed is True
    assert result.expired is False
    assert result.remaining_seconds > 0


@pytest.mark.asyncio
async def test_deadline_stops_slow_operation() -> None:
    controller = RuntimeDeadlineController(RuntimeDeadline.after(0.02))

    async def operation():
        await asyncio.sleep(1)

    result = await controller.execute(operation)

    assert result.completed is False
    assert result.expired is True
    assert result.remaining_seconds == 0.0


@pytest.mark.asyncio
async def test_expired_deadline_rejects_operation() -> None:
    deadline = RuntimeDeadline(
        datetime.now(UTC) - timedelta(seconds=1)
    )

    called = False

    async def operation():
        nonlocal called
        called = True

    result = await RuntimeDeadlineController(deadline).execute(operation)

    assert result.completed is False
    assert result.expired is True
    assert called is False
