from unittest.mock import AsyncMock, patch

import httpx
import pytest

from runtime.models.messages import ModelRequest, ModelResponse
from runtime.providers.ollama import OllamaProvider
from runtime.service import AIRuntime


@pytest.mark.asyncio
async def test_runtime_rejects_empty_prompt() -> None:
    provider = AsyncMock()
    runtime = AIRuntime(provider)

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await runtime.generate(ModelRequest(prompt="   "))


@pytest.mark.asyncio
async def test_runtime_delegates_to_provider() -> None:
    provider = AsyncMock()
    provider.generate.return_value = ModelResponse(
        content="Hello",
        model="test-model",
        provider="test",
    )

    runtime = AIRuntime(provider)

    result = await runtime.generate(
        ModelRequest(prompt="Say hello", model="test-model")
    )

    assert result.content == "Hello"
    provider.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_ollama_generate() -> None:
    provider = OllamaProvider(
        base_url="http://ollama.test",
        default_model="test-model",
    )

    response = httpx.Response(
        200,
        json={
            "response": "Hello from Ollama",
            "model": "test-model",
        },
        request=httpx.Request("POST", "http://ollama.test/api/generate"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response

        result = await provider.generate(
            ModelRequest(prompt="Say hello")
        )

    assert result.content == "Hello from Ollama"
    assert result.model == "test-model"
    assert result.provider == "ollama"


@pytest.mark.asyncio
async def test_ollama_health_success() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")

    response = httpx.Response(
        200,
        json={"models": []},
        request=httpx.Request("GET", "http://ollama.test/api/tags"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response

        assert await provider.health() is True


@pytest.mark.asyncio
async def test_ollama_health_failure() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")

    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("connection failed"),
    ):
        assert await provider.health() is False
