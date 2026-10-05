import pytest

from company.distributed import DistributedExecutor, Worker


def test_distributed_round_robin_and_retry() -> None:
    executor = DistributedExecutor((Worker("w1"), Worker("w2")))
    assert executor.execute(executor.submit("a"), lambda x: x.upper()).value == "A"
    assert executor.execute(executor.submit("b"), lambda x: x.upper()).worker_id == "w2"

    attempts = {"n": 0}

    def flaky(value: object) -> object:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("temporary")
        return value

    assert executor.execute_with_retry(executor.submit("ok"), flaky).success


def test_no_ready_worker() -> None:
    executor = DistributedExecutor((Worker("w", status="offline"),))
    with pytest.raises(RuntimeError):
        executor.execute(executor.submit("x"), lambda value: value)
