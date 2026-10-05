from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.0
    max_tokens: int | None = None


@dataclass(frozen=True)
class AIResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, Any] | None = None
    raw: Any = None


class AIModel(Protocol):
    def generate(self, request: AIRequest) -> AIResponse:
        ...
