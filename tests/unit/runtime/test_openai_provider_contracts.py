from unittest.mock import AsyncMock, patch

import httpx
import pytest

from runtime.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_provider_rejects_malformed_json_without_echoing_body() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="",
    )
    response = httpx.Response(
        200,
        text="private-prompt-fragment",
        request=httpx.Request("POST", "http://model.test/v1/chat/completions"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="invalid JSON") as error:
            await provider.generate_payload({"prompt": "hello"})
    assert "private-prompt-fragment" not in str(error.value)


@pytest.mark.asyncio
async def test_openai_provider_sanitizes_transport_errors() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="",
    )
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("private-prompt-fragment"),
    ):
        with pytest.raises(RuntimeError, match="Could not reach") as error:
            await provider.generate_payload({"prompt": "hello"})
    assert "private-prompt-fragment" not in str(error.value)


@pytest.mark.asyncio
async def test_openai_provider_tolerates_malformed_usage_metadata() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="",
    )
    response = httpx.Response(
        200,
        json={"choices": [{"message": {"content": "ok"}}], "usage": "unexpected"},
        request=httpx.Request("POST", "http://model.test/v1/chat/completions"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        content, metrics = await provider.generate_payload({"prompt": "hello"})
    assert content == "ok"
    assert metrics["prompt_tokens"] is None
    assert metrics["generated_tokens"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code, expected", [(200, True), (401, True), (403, True), (404, False), (503, False)])
async def test_openai_provider_health_checks_endpoint_status(
    status_code: int, expected: bool
) -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="",
    )
    response = httpx.Response(
        status_code,
        request=httpx.Request("GET", "http://model.test/v1/models"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = response
        assert await provider.health() is expected


@pytest.mark.asyncio
async def test_openai_provider_health_returns_false_on_transport_failure() -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://model.test/v1",
        api_key="",
    )
    with patch(
        "httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("offline"),
    ):
        assert await provider.health() is False
