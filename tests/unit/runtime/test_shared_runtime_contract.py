from unittest.mock import AsyncMock

import pytest

from runtime.models.messages import ModelRequest, ModelResponse
from runtime.service import AIRuntime


def provider_with_response(response: object) -> AsyncMock:
    provider = AsyncMock()
    provider.name = "test-provider"
    provider.generate.return_value = response
    provider.health.return_value = True
    return provider


@pytest.mark.asyncio
async def test_runtime_rejects_non_model_response() -> None:
    provider = provider_with_response({"content": "not typed"})
    with pytest.raises(TypeError, match="must return a ModelResponse"):
        await AIRuntime(provider).generate(ModelRequest(prompt="hello"))


@pytest.mark.asyncio
async def test_runtime_rejects_empty_provider_generation() -> None:
    provider = provider_with_response(
        ModelResponse(content=" ", model="model-a", provider="test-provider")
    )
    with pytest.raises(RuntimeError, match="empty generation"):
        await AIRuntime(provider).generate(ModelRequest(prompt="hello"))


@pytest.mark.asyncio
async def test_runtime_rejects_empty_model_identifier() -> None:
    provider = provider_with_response(
        ModelResponse(content="ok", model=" ", provider="test-provider")
    )
    with pytest.raises(RuntimeError, match="empty model identifier"):
        await AIRuntime(provider).generate(ModelRequest(prompt="hello"))


@pytest.mark.asyncio
async def test_runtime_rejects_inconsistent_provider_metadata() -> None:
    provider = provider_with_response(
        ModelResponse(content="ok", model="model-a", provider="wrong-provider")
    )
    with pytest.raises(RuntimeError, match="inconsistent provider metadata"):
        await AIRuntime(provider).generate(ModelRequest(prompt="hello"))


@pytest.mark.asyncio
async def test_runtime_rejects_negative_duration_metadata() -> None:
    provider = provider_with_response(
        ModelResponse(
            content="ok",
            model="model-a",
            provider="test-provider",
            duration_ms=-1,
        )
    )
    with pytest.raises(RuntimeError, match="invalid duration metadata"):
        await AIRuntime(provider).generate(ModelRequest(prompt="hello"))


@pytest.mark.asyncio
async def test_runtime_health_requires_boolean_contract() -> None:
    provider = provider_with_response(
        ModelResponse(content="ok", model="model-a", provider="test-provider")
    )
    provider.health.return_value = "yes"
    with pytest.raises(TypeError, match="health must return a boolean"):
        await AIRuntime(provider).health()
