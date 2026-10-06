from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Experiment:
    name: str
    control: str
    treatment: str


@dataclass(frozen=True, slots=True)
class VariantResult:
    variant: str
    metric: float


class ExperimentService:
    """Records deterministic experiment results and selects the strongest variant."""

    def winner(self, experiment: Experiment, results: list[VariantResult]) -> str:
        if not results:
            raise ValueError("results must not be empty")
        allowed = {experiment.control, experiment.treatment}
        valid = [item for item in results if item.variant in allowed]
        if not valid:
            raise ValueError("results contain no experiment variants")
        return max(valid, key=lambda item: item.metric).variant
