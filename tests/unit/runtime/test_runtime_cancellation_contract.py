import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from runtime.models.messages import ModelRequest
from runtime.providers.ollama import OllamaProvider
from runtime.providers.openai_compatible import OpenAICompatibleProvider
from runtime.service import AIRuntime


@pytest.mark.asyncio
async def test_ollama_cancellation_propagates_without_retry() -> None:
    provider = OllamaProvider(base_url="http://ollama.test")
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked_post(*args, **kwargs):
        started.set()
        await release.wait()
        return httpx.Response(
            200,
            json={"response": "late"},
            request=httpx.Request("POST", "http://ollama.test/api/generate"),
        )

    import httpx

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=blocked_post) as post:
        task = asyncio.create_task(provider.generate(ModelRequest(prompt="hello")))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    post.assert_awaited_once()


@pytest.mark.asyncio
async def test_openai_compatible_cancellation_propagates_without_retry() -> None:
    provider = OpenAICompatibleProvider(base_url="http://model.test/v1", api_key="")
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked_post(*args, **kwargs):
        started.set()
        await release.wait()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "late"}}]},
            request=httpx.Request("POST", "http://model.test/v1/chat/completions"),
        )

    import httpx

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=blocked_post) as post:
        task = asyncio.create_task(provider.generate(ModelRequest(prompt="hello")))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    post.assert_awaited_once()


@pytest.mark.asyncio
async def test_shared_runtime_does_not_swallow_provider_cancellation() -> None:
    provider = AsyncMock()
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked_generate(request):
        started.set()
        await release.wait()
        raise AssertionError("cancelled execution must not resume")

    provider.generate.side_effect = blocked_generate
    provider.name = "test-provider"
    runtime = AIRuntime(provider)
    task = asyncio.create_task(runtime.generate(ModelRequest(prompt="hello")))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    provider.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_ollama_timeout_is_bounded_and_sanitized() -> None:
    provider = OllamaProvider(base_url="http://ollama.test", timeout=0.1)
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("private request data"),
    ):
        with pytest.raises(RuntimeError, match="timed out after 0.1s") as error:
            await provider.generate(ModelRequest(prompt="hello"))
    assert "private request data" not in str(error.value)


import httpx
