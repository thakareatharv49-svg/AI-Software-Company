from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceAllocation:
    project: str
    budget: float
    capacity: float


class ResourceAllocator:
    def allocate(self, project: str, budget: float, capacity: float) -> ResourceAllocation:
        if budget < 0 or capacity < 0:
            raise ValueError("budget and capacity must be non-negative")
        return ResourceAllocation(project, budget, capacity)
