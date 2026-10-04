from __future__ import annotations

import pytest

from company.runtime.circuit import (
    CircuitOpenError,
    CircuitProtectedRuntime,
    RuntimeCircuitBreaker,
)


class FakeRuntime:
    async def execute(self, operation):
        return await operation()


@pytest.mark.asyncio
async def test_circuit_starts_closed() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=3)

    assert await circuit.allow() is True

    state = await circuit.state()

    assert state.failures == 0
    assert state.open is False


@pytest.mark.asyncio
async def test_circuit_opens_after_failure_threshold() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=2)

    await circuit.record_failure()
    assert await circuit.allow() is True

    await circuit.record_failure()

    assert await circuit.allow() is False

    state = await circuit.state()

    assert state.failures == 2
    assert state.open is True


@pytest.mark.asyncio
async def test_circuit_success_resets_failures() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=3)

    await circuit.record_failure()
    await circuit.record_failure()
    state = await circuit.record_success()

    assert state.failures == 0
    assert state.open is False
    assert await circuit.allow() is True


@pytest.mark.asyncio
async def test_circuit_can_be_reset() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=1)

    await circuit.record_failure()
    assert await circuit.allow() is False

    state = await circuit.reset()

    assert state.failures == 0
    assert state.open is False
    assert await circuit.allow() is True


@pytest.mark.asyncio
async def test_protected_runtime_records_failure() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=2)
    runtime = CircuitProtectedRuntime(FakeRuntime(), circuit)

    async def operation():
        raise RuntimeError("failure")

    with pytest.raises(RuntimeError, match="failure"):
        await runtime.execute(operation)

    state = await circuit.state()

    assert state.failures == 1
    assert state.open is False


@pytest.mark.asyncio
async def test_protected_runtime_opens_after_repeated_failures() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=2)
    runtime = CircuitProtectedRuntime(FakeRuntime(), circuit)

    async def operation():
        raise RuntimeError("failure")

    for _ in range(2):
        with pytest.raises(RuntimeError, match="failure"):
            await runtime.execute(operation)

    with pytest.raises(CircuitOpenError, match="circuit is open"):
        await runtime.execute(operation)


@pytest.mark.asyncio
async def test_protected_runtime_success_closes_circuit() -> None:
    circuit = RuntimeCircuitBreaker(failure_threshold=2)
    runtime = CircuitProtectedRuntime(FakeRuntime(), circuit)

    async def failure():
        raise RuntimeError("failure")

    async def success():
        return "success"

    with pytest.raises(RuntimeError):
        await runtime.execute(failure)

    result = await runtime.execute(success)

    assert result == "success"

    state = await circuit.state()

    assert state.failures == 0
    assert state.open is False


def test_invalid_failure_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        RuntimeCircuitBreaker(failure_threshold=0)
