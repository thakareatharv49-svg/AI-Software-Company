from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ProductState(StrEnum):
    BUILD = "build"
    DEPLOYED = "deployed"
    MONITORING = "monitoring"
    IMPROVEMENT = "improvement"
    RELEASED = "released"
    PAUSED = "paused"


@dataclass(frozen=True)
class ProductSignal:
    kind: str
    detail: str
    priority: int = 1


@dataclass
class ProductLifecycle:
    product_id: str
    state: ProductState = ProductState.BUILD
    backlog: list[ProductSignal] = field(default_factory=list)
    version: int = 0

    def deploy(self) -> None:
        if self.state not in (ProductState.BUILD, ProductState.RELEASED):
            raise ValueError("product cannot deploy from current state")
        self.state = ProductState.DEPLOYED

    def monitor(self) -> None:
        if self.state != ProductState.DEPLOYED:
            raise ValueError("product must be deployed")
        self.state = ProductState.MONITORING

    def ingest(self, signal: ProductSignal) -> None:
        if self.state not in (ProductState.MONITORING, ProductState.DEPLOYED):
            raise ValueError("product is not operational")
        self.backlog.append(signal)
        self.state = ProductState.IMPROVEMENT

    def release(self) -> int:
        if self.state != ProductState.IMPROVEMENT:
            raise ValueError("no improvement ready")
        self.version += 1
        self.backlog.clear()
        self.state = ProductState.RELEASED
        return self.version

    def pause(self) -> None:
        self.state = ProductState.PAUSED
