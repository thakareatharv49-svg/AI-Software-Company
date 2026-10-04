from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import psutil


class ResourceLimitExceeded(RuntimeError):
    """Raised when a runtime resource policy is exceeded."""


@dataclass(slots=True, frozen=True)
class RuntimeResourcePolicy:
    max_runtime_seconds: float | None = None
    max_memory_mb: float | None = None
    max_cpu_percent: float | None = None
    sample_interval_seconds: float = 0.05

    def __post_init__(self) -> None:
        if self.max_runtime_seconds is not None and self.max_runtime_seconds <= 0:
            raise ValueError("max_runtime_seconds must be positive")

        if self.max_memory_mb is not None and self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")

        if self.max_cpu_percent is not None and not 0 < self.max_cpu_percent <= 100:
            raise ValueError("max_cpu_percent must be between 0 and 100")

        if self.sample_interval_seconds <= 0:
            raise ValueError("sample_interval_seconds must be positive")


@dataclass(slots=True, frozen=True)
class RuntimeResourceUsage:
    elapsed_seconds: float
    memory_mb: float
    cpu_percent: float


class RuntimeResourceEnforcer:
    """Enforces wall-clock, memory and CPU limits around an async runtime task."""

    def __init__(
        self,
        policy: RuntimeResourcePolicy | None = None,
    ) -> None:
        self.policy = policy or RuntimeResourcePolicy()
        self._process = psutil.Process()

    def usage(self, started_at: float) -> RuntimeResourceUsage:
        elapsed = max(0.0, time.monotonic() - started_at)
        memory_mb = self._process.memory_info().rss / (1024 * 1024)
        cpu_percent = self._process.cpu_percent(interval=None)

        return RuntimeResourceUsage(
            elapsed_seconds=elapsed,
            memory_mb=memory_mb,
            cpu_percent=cpu_percent,
        )

    def _check(self, usage: RuntimeResourceUsage) -> None:
        policy = self.policy

        if (
            policy.max_runtime_seconds is not None
            and usage.elapsed_seconds > policy.max_runtime_seconds
        ):
            raise ResourceLimitExceeded(
                f"runtime limit exceeded: "
                f"{usage.elapsed_seconds:.3f}s > "
                f"{policy.max_runtime_seconds:.3f}s"
            )

        if (
            policy.max_memory_mb is not None
            and usage.memory_mb > policy.max_memory_mb
        ):
            raise ResourceLimitExceeded(
                f"memory limit exceeded: "
                f"{usage.memory_mb:.2f}MB > "
                f"{policy.max_memory_mb:.2f}MB"
            )

        if (
            policy.max_cpu_percent is not None
            and usage.cpu_percent > policy.max_cpu_percent
        ):
            raise ResourceLimitExceeded(
                f"CPU limit exceeded: "
                f"{usage.cpu_percent:.2f}% > "
                f"{policy.max_cpu_percent:.2f}%"
            )

    async def run(self, target):
        if not callable(target):
            raise TypeError("target must be callable")

        started_at = time.monotonic()
        self._process.cpu_percent(interval=None)

        task = asyncio.create_task(target())

        try:
            while not task.done():
                usage = self.usage(started_at)
                self._check(usage)

                if (
                    self.policy.max_runtime_seconds is not None
                    and usage.elapsed_seconds >= self.policy.max_runtime_seconds
                ):
                    raise ResourceLimitExceeded(
                        f"runtime limit exceeded: "
                        f"{usage.elapsed_seconds:.3f}s >= "
                        f"{self.policy.max_runtime_seconds:.3f}s"
                    )

                await asyncio.sleep(self.policy.sample_interval_seconds)

            result = await task

            usage = self.usage(started_at)
            self._check(usage)

            return result

        except ResourceLimitExceeded:
            if not task.done():
                task.cancel()

            await asyncio.gather(task, return_exceptions=True)
            raise

        except asyncio.CancelledError:
            if not task.done():
                task.cancel()

            await asyncio.gather(task, return_exceptions=True)
            raise

        except Exception:
            await asyncio.gather(task, return_exceptions=True)
            raise
