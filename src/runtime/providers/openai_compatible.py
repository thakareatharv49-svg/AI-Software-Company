from __future__ import annotations

import math
import time

import httpx

from config.settings import settings
from runtime.models.messages import ModelRequest, ModelResponse
from runtime.providers.base import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    """Call OpenAI Chat Completions-compatible hosted or self-hosted endpoints.

    Works with OpenAI-compatible gateways and local servers (for example vLLM,
    LM Studio, or compatible proxies). A bearer token is sent only when configured.
    """

    name = "openai-compatible"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        configured_url = (
            settings.openai_compatible_base_url if base_url is None else base_url
        )
        configured_model = (
            settings.openai_compatible_model if default_model is None else default_model
        )
        configured_timeout = (
            settings.openai_compatible_timeout if timeout is None else timeout
        )
        self.base_url = configured_url.strip().rstrip("/")
        self.api_key = settings.openai_compatible_api_key if api_key is None else api_key
        self.default_model = configured_model.strip()
        self.timeout = float(configured_timeout)

        if not self.base_url:
            raise ValueError("OpenAI-compatible base URL cannot be empty.")
        if not self.default_model:
            raise ValueError("OpenAI-compatible default model cannot be empty.")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("OpenAI-compatible timeout must be a finite positive number.")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        model = (request.model or self.default_model).strip()
        if not model:
            raise ValueError("Model cannot be empty.")
        content, metrics = await self.generate_payload(
            {
                "model": model,
                "prompt": request.prompt,
                "system": request.system,
                "options": {"temperature": request.temperature},
            }
        )
        return ModelResponse(
            content=content,
            model=model,
            provider=self.name,
            duration_ms=metrics.get("duration_ms"),
        )

    async def generate_payload(
        self, payload: dict
    ) -> tuple[str, dict[str, int | None]]:
        """Generate from the factory's richer Ollama-shaped payload."""
        model = str(payload.get("model") or self.default_model).strip()
        prompt = str(payload.get("prompt") or "")
        if not model:
            raise ValueError("Model cannot be empty.")
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        messages = []
        if payload.get("system"):
            messages.append({"role": "system", "content": str(payload["system"])})
        messages.append({"role": "user", "content": prompt})
        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
        body: dict = {
            "model": model,
            "messages": messages,
            "temperature": options.get("temperature", 0.2),
            "stream": False,
        }
        if isinstance(options.get("num_predict"), int):
            body["max_tokens"] = options["num_predict"]
        if payload.get("format"):
            body["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=body,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"OpenAI-compatible request timed out after {self.timeout:g}s."
            ) from exc
        except httpx.HTTPStatusError as exc:
            # Never include response bodies: upstream error pages can echo credentials
            # or private prompts, and provider URLs can contain user-info credentials.
            raise RuntimeError(
                f"OpenAI-compatible provider returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("Could not reach the OpenAI-compatible provider.") from exc
        except ValueError as exc:
            raise RuntimeError(
                "OpenAI-compatible provider returned an invalid JSON response."
            ) from exc

        choices = data.get("choices") if isinstance(data, dict) else None
        content = None
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "OpenAI-compatible provider returned an empty or invalid generation."
            )

        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        metrics: dict[str, int | None] = {
            "prompt_tokens": (
                usage.get("prompt_tokens")
                if isinstance(usage, dict) and isinstance(usage.get("prompt_tokens"), int)
                else None
            ),
            "generated_tokens": (
                usage.get("completion_tokens")
                if isinstance(usage, dict)
                and isinstance(usage.get("completion_tokens"), int)
                else None
            ),
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
        return content, metrics

    async def health(self) -> bool:
        # Chat-completions-compatible providers do not share a standard health URL.
        # A lightweight models-list request is conventional; auth failures still
        # indicate reachability, while server and transport failures indicate unhealthy.
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
                return response.status_code < 500
        except (httpx.HTTPError, OSError):
            return False
