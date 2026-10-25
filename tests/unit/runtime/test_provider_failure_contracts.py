from unittest.mock import AsyncMock, patch

import httpx
import pytest

from runtime.models.messages import ModelRequest
from runtime.providers.ollama import OllamaProvider
from runtime.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_ollama_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="finite positive"):
        OllamaProvider(base_url="http://ollama.test", timeout=timeout)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_openai_compatible_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="finite positive"):
        OpenAICompatibleProvider(base_url="http://model.test/v1", timeout=timeout)


@pytest.mark.asyncio
async def test_ollama_rejects_empty_generation() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")
    response = httpx.Response(
        200,
        json={"response": ""},
        request=httpx.Request("POST", "http://ollama.test/api/generate"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="empty generation"):
            await provider.generate(ModelRequest(prompt="Build a project"))


@pytest.mark.asyncio
async def test_ollama_reports_invalid_json_without_raw_body() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")
    response = httpx.Response(
        200,
        text="credential=must-not-leak",
        request=httpx.Request("POST", "http://ollama.test/api/generate"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="invalid JSON") as error:
            await provider.generate(ModelRequest(prompt="Build a project"))
    assert "must-not-leak" not in str(error.value)


@pytest.mark.asyncio
async def test_openai_compatible_http_error_does_not_expose_body_or_credentials() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="top-secret-token",
    )
    response = httpx.Response(
        401,
        text="Authorization failed for token top-secret-token",
        request=httpx.Request("POST", "http://model.test/v1/chat/completions"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="HTTP 401") as error:
            await provider.generate(ModelRequest(prompt="Build a project"))
    assert "top-secret-token" not in str(error.value)
    assert "Authorization failed" not in str(error.value)


@pytest.mark.asyncio
async def test_openai_compatible_rejects_empty_generation() -> None:
    provider = OpenAICompatibleProvider(base_url="http://model.test/v1", api_key="")
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "  "}}]},
        request=httpx.Request("POST", "http://model.test/v1/chat/completions"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="empty or invalid generation"):
            await provider.generate(ModelRequest(prompt="Build a project"))


@pytest.mark.asyncio
async def test_openai_compatible_timeout_error_is_sanitized() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="top-secret-token",
        timeout=0.25,
    )
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("token top-secret-token"),
    ):
        with pytest.raises(RuntimeError, match="timed out after 0.25s") as error:
            await provider.generate(ModelRequest(prompt="Build a project"))
    assert "top-secret-token" not in str(error.value)


@pytest.mark.asyncio
async def test_openai_compatible_rejects_empty_prompt_before_network_call() -> None:
    provider = OpenAICompatibleProvider(base_url="http://model.test/v1", api_key="")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await provider.generate_payload({"prompt": "   "})
    mock_post.assert_not_awaited()
