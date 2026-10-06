import asyncio

import pytest

from src.company.workforce import AgentWorkerPool, AgentWorkItem


@pytest.mark.asyncio
async def test_worker_pool_runs_bounded_work_and_isolates_failures():
    active = 0
    peak = 0

    async def worker(item):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        if item.task_id == "bad":
            raise RuntimeError("failed worker")
        return item.task_id

    pool = AgentWorkerPool(worker, max_concurrency=2)
    results = await pool.execute(
        [AgentWorkItem(str(i), "agent", None) for i in range(4)]
        + [AgentWorkItem("bad", "agent", None)]
    )

    assert peak <= 2
    assert sum(result.success for result in results) == 4
    assert next(result for result in results if result.task_id == "bad").error == "failed worker"
