from __future__ import annotations

import time

import httpx

from src.config.settings import settings


class OpenAICompatibleProvider:
    """Call OpenAI Chat Completions-compatible hosted or self-hosted endpoints.

    Works with OpenAI-compatible gateways and local servers (for example vLLM,
    LM Studio, or compatible proxies). A bearer token is sent only when configured.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None, default_model: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or settings.openai_compatible_base_url).rstrip("/")
        self.api_key = settings.openai_compatible_api_key if api_key is None else api_key
        self.default_model = default_model or settings.openai_compatible_model
        self.timeout = timeout or settings.openai_compatible_timeout

    async def generate(self, payload: dict) -> tuple[str, dict[str, int | None]]:
        model = str(payload.get("model") or self.default_model)
        prompt = str(payload.get("prompt") or "")
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
                response = await client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"OpenAI-compatible provider timed out after {self.timeout:g}s for model '{model}'.") from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500].replace("\\n", " ")
            raise RuntimeError(f"OpenAI-compatible provider returned HTTP {exc.response.status_code} for model '{model}': {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Could not reach OpenAI-compatible provider at {self.base_url}: {exc}") from exc
        except ValueError as exc:
            raise RuntimeError(f"OpenAI-compatible provider returned a non-JSON response for model '{model}'.") from exc
        choices = data.get("choices") if isinstance(data, dict) else None
        content = None
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            message = choices[0].get("message")
            if isinstance(message, dict):
                content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"OpenAI-compatible provider returned an empty generation for model '{model}'.")
        usage = data.get("usage", {}) if isinstance(data, dict) else {}
        metrics: dict[str, int | None] = {
            "prompt_tokens": usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None,
            "generated_tokens": usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"), int) else None,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
        return content, metrics

    async def health(self) -> bool:
        # Chat-completions-compatible providers do not share a standard health URL.
        # A lightweight models-list request is conventional; auth failures mean the
        # endpoint is reachable, while transport/server failures indicate unhealthy.
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
                return response.status_code < 500
        except (httpx.HTTPError, OSError):
            return False
