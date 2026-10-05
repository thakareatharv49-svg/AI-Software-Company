from __future__ import annotations

from company.ai.model import AIModel


class AIModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, AIModel] = {}

    def register(self, name: str, model: AIModel) -> None:
        if not name.strip():
            raise ValueError("Model name must not be empty")
        self._models[name] = model

    def get(self, name: str) -> AIModel:
        try:
            return self._models[name]
        except KeyError as exc:
            raise KeyError(f"AI model is not registered: {name}") from exc

    def has(self, name: str) -> bool:
        return name in self._models

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._models))
