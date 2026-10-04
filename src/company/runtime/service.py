from __future__ import annotations

from typing import Any

from src.company.runtime.autonomous import AutonomousRuntime
from src.company.runtime.config import RuntimeConfig
from src.company.runtime.persistent_run_store import PersistentRunStore


class CompanyRuntimeService:
    def __init__(
        self,
        pipeline: Any,
        *,
        config: RuntimeConfig | None = None,
    ) -> None:
        if pipeline is None:
            raise ValueError("pipeline is required")

        self.config = config or RuntimeConfig.from_environment()
        self.runtime = AutonomousRuntime(
            pipeline,
            dispatcher=self._build_dispatcher(),
        )
        self._started = False
        self.persistent_store = PersistentRunStore()

    def _build_dispatcher(self):
        from src.company.runtime.dispatcher import RuntimeDispatcher

        return RuntimeDispatcher(
            max_queue_size=self.config.max_concurrent_runs,
            worker_count=self.config.max_concurrent_runs,
        )

    async def start(self) -> None:
        if self._started:
            return

        await self.runtime.start()
        self._started = True

    async def run(self, **kwargs: Any):
        if not self._started:
            raise RuntimeError("Company runtime service is not running.")

        return await self.runtime.run(**kwargs)

    async def get_run(self, run_id: str):
        if not self._started:
            raise RuntimeError("Company runtime service is not running.")
        return await self.runtime.get_run(run_id)

    async def stop(self) -> None:
        if not self._started:
            return

        await self.runtime.stop()
        self._started = False

    async def state(self):
        return await self.runtime.state()
