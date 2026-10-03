from runtime.models.messages import ModelRequest, ModelResponse
from runtime.providers.base import ModelProvider


class AIRuntime:
    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if not request.prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        return await self.provider.generate(request)

    async def health(self) -> bool:
        return await self.provider.health()
