from unittest.mock import AsyncMock, patch

import httpx
import pytest

from config.settings import settings
from src.company.project_generator import OllamaProjectGenerator


@pytest.mark.asyncio
async def test_factory_generator_uses_configured_ollama_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "factory_model_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.test")
    monkeypatch.setattr(settings, "ollama_model", "test-model")
    monkeypatch.setattr(settings, "ollama_timeout", 2.0)
    response = httpx.Response(
        200,
        json={
            "response": '{"files":{"main.py":"print(1)"}}',
            "model": "test-model",
            "prompt_eval_count": 12,
            "eval_count": 5,
        },
        request=httpx.Request("POST", "http://ollama.test/api/generate"),
    )
    generator = OllamaProjectGenerator()
    payload = {
        "model": "test-model",
        "prompt": "Return a project JSON object",
        "format": "json",
        "options": {"temperature": 0.1},
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        result = await generator._call(payload)

    assert result == '{"files":{"main.py":"print(1)"}}'
    request = mock_post.await_args
    assert request.args[0] == "http://ollama.test/api/generate"
    assert request.kwargs["json"]["model"] == "test-model"
    assert request.kwargs["json"]["format"] == "json"


@pytest.mark.asyncio
async def test_factory_generator_uses_configured_openai_compatible_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "factory_model_provider", "openai-compatible")
    monkeypatch.setattr(settings, "openai_compatible_base_url", "http://model.test/v1")
    monkeypatch.setattr(settings, "openai_compatible_api_key", "")
    monkeypatch.setattr(settings, "openai_compatible_model", "compatible-model")
    monkeypatch.setattr(settings, "openai_compatible_timeout", 2.0)
    response = httpx.Response(
        200,
        json={
            "choices": [
                {"message": {"content": '{"files":{"main.py":"print(1)"}}'}}
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5},
        },
        request=httpx.Request("POST", "http://model.test/v1/chat/completions"),
    )
    generator = OllamaProjectGenerator()
    payload = {
        "model": "compatible-model",
        "prompt": "Return a project JSON object",
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        result = await generator._call(payload)

    assert result == '{"files":{"main.py":"print(1)"}}'
    request = mock_post.await_args
    assert request.args[0] == "http://model.test/v1/chat/completions"
    assert request.kwargs["json"]["model"] == "compatible-model"
    assert request.kwargs["json"]["response_format"] == {"type": "json_object"}
    assert request.kwargs["json"]["max_tokens"] == 2048
