from __future__ import annotations

from company.ai.model import AIRequest, AIResponse


class DeterministicAIModel:
    def __init__(
        self,
        *,
        name: str = "deterministic",
        response: str = "ok",
    ) -> None:
        self.name = name
        self.response = response
        self.requests: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResponse:
        self.requests.append(request)

        return AIResponse(
            content=self.response,
            model=self.name,
            provider="local",
        )
