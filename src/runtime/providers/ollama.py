import math
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
        configured_url = settings.ollama_base_url if base_url is None else base_url
        configured_model = settings.ollama_model if default_model is None else default_model
        configured_timeout = settings.ollama_timeout if timeout is None else timeout
        self.base_url = configured_url.strip().rstrip("/")
        self.default_model = configured_model.strip()
        self.timeout = float(configured_timeout)

        if not self.base_url:
            raise ValueError("Ollama base URL cannot be empty.")
        if not self.default_model:
            raise ValueError("Ollama default model cannot be empty.")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("Ollama timeout must be a finite positive number.")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        model = (request.model or self.default_model).strip()
        if not model:
            raise ValueError("Model cannot be empty.")
        if not request.prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": model,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        if request.system:
            payload["system"] = request.system

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Ollama request timed out after {self.timeout:g}s."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("Could not reach the Ollama provider.") from exc
        except ValueError as exc:
            raise RuntimeError("Ollama returned an invalid JSON response.") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Ollama returned an invalid response shape.")
        content = data.get("response")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned an empty generation.")
        returned_model = data.get("model")
        duration_ms = int((time.perf_counter() - started) * 1000)

        return ModelResponse(
            content=content,
            model=returned_model if isinstance(returned_model, str) and returned_model else model,
            provider=self.name,
            duration_ms=duration_ms,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
            return isinstance(data, dict) and isinstance(data.get("models"), list)
        except (httpx.HTTPError, OSError, ValueError):
            return False
