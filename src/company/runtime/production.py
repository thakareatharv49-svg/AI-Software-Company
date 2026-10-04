from __future__ import annotations

from collections.abc import Awaitable, Callable

from .alerts import RuntimeAlertManager
from .backpressure import RuntimeBackpressureController
from .config import RuntimeConfig
from .coordinator import RuntimeCoordinator
from .metrics import RuntimeMetricsCollector
from .timeouts import RuntimeTimeoutController


class ProductionRuntime:
    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self.config = config or RuntimeConfig.from_environment()
        self.coordinator = RuntimeCoordinator(
            max_concurrent_runs=self.config.max_concurrent_runs
        )
        self.metrics = RuntimeMetricsCollector()
        self.alerts = RuntimeAlertManager()
        self.backpressure = RuntimeBackpressureController(
            max_tasks=self.config.max_concurrent_runs
        )
        self.timeout = RuntimeTimeoutController(
            timeout_seconds=float(self.config.shutdown_timeout_seconds)
        )
        self._running = False

    async def start(self) -> None:
        if self._running:
            return

        await self.coordinator.start()
        self._running = True

    async def stop(self) -> None:
        if not self._running:
            return

        await self.coordinator.stop()
        self._running = False

    async def execute(
        self,
        operation: Callable[[], Awaitable[object]],
    ) -> object:
        if not self._running:
            raise RuntimeError("production runtime is not running")

        capacity = await self.backpressure.acquire()

        if not capacity.allowed:
            await self.alerts.check(
                metric="capacity_rejections",
                value=1,
                threshold=0,
                message="runtime capacity exceeded",
                level="warning",
            )
            raise RuntimeError("runtime capacity exceeded")

        await self.metrics.started()

        try:
            async def coordinated_operation() -> object:
                result = await self.timeout.execute(operation)

                if result.timed_out:
                    await self.alerts.check(
                        metric="timeouts",
                        value=1,
                        threshold=0,
                        message="runtime operation timed out",
                        level="error",
                    )
                    raise TimeoutError("runtime operation timed out")

                return result

            timeout_result = await self.coordinator.execute(
                coordinated_operation
            )

            await self.metrics.completed()
            return timeout_result

        except Exception as exc:
            await self.metrics.failed()

            await self.alerts.check(
                metric="execution_failures",
                value=1,
                threshold=0,
                message=str(exc),
                level="error",
            )

            raise

        finally:
            await self.backpressure.release()

    async def status(self) -> dict[str, object]:
        coordinator_status = await self.coordinator.status()
        metrics = await self.metrics.snapshot()
        capacity = await self.backpressure.status()
        alerts = await self.alerts.alerts()

        return {
            "running": self._running,
            "active_runs": coordinator_status.active_runs,
            "max_concurrent_runs": coordinator_status.max_concurrent_runs,
            "metrics": metrics,
            "capacity": capacity,
            "alerts": alerts,
        }
