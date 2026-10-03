import time

import httpx

from config.settings import settings
from runtime.models.messages import ModelRequest, ModelResponse
from runtime.providers.base import ModelProvider


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.default_model = default_model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

    async def generate(self, request: ModelRequest) -> ModelResponse:
        model = request.model or self.default_model

        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }

        if request.system:
            payload["system"] = request.system

        started = time.perf_counter()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        duration_ms = int((time.perf_counter() - started) * 1000)

        return ModelResponse(
            content=data.get("response", ""),
            model=data.get("model", model),
            provider=self.name,
            duration_ms=duration_ms,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            return True
        except (httpx.HTTPError, OSError):
            return False
