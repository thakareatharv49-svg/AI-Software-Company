from runtime.models.messages import ModelRequest, ModelResponse
from runtime.providers.base import ModelProvider


class AIRuntime:
    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    async def generate(self, request: ModelRequest) -> ModelResponse:
        if not request.prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = await self.provider.generate(request)
        if not isinstance(response, ModelResponse):
            raise TypeError("Model provider must return a ModelResponse.")
        if not response.content.strip():
            raise RuntimeError("Model provider returned an empty generation.")
        if not response.model.strip():
            raise RuntimeError("Model provider returned an empty model identifier.")

        provider_name = getattr(self.provider, "name", None)
        if (
            isinstance(provider_name, str)
            and provider_name
            and response.provider != provider_name
        ):
            raise RuntimeError("Model provider returned inconsistent provider metadata.")
        if response.duration_ms is not None and response.duration_ms < 0:
            raise RuntimeError("Model provider returned invalid duration metadata.")

        return response

    async def health(self) -> bool:
        healthy = await self.provider.health()
        if not isinstance(healthy, bool):
            raise TypeError("Model provider health must return a boolean.")
        return healthy
