from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.runtime.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_json_generation_request() -> None:
    provider = OpenAICompatibleProvider(base_url="http://model.test/v1", api_key="secret", default_model="test-model")
    response = httpx.Response(200, json={"choices": [{"message": {"content": '{"files": {}}'}}], "usage": {"prompt_tokens": 12, "completion_tokens": 4}}, request=httpx.Request("POST", "http://model.test/v1/chat/completions"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        content, metrics = await provider.generate_payload({"prompt": "Build app", "model": "test-model", "format": {"type": "object"}, "options": {"temperature": 0.1, "num_predict": 2048}})
    assert content == '{"files": {}}'
    assert metrics["prompt_tokens"] == 12
    request = mock_post.await_args.kwargs
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert request["json"]["max_tokens"] == 2048
    assert request["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_openai_compatible_provider_omits_auth_when_no_key_configured() -> None:
    provider = OpenAICompatibleProvider(base_url="http://local.test/v1", api_key="", default_model="local-model")
    response = httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]}, request=httpx.Request("POST", "http://local.test/v1/chat/completions"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        content, _ = await provider.generate_payload({"prompt": "hello"})
    assert content == "ok"
    assert "Authorization" not in mock_post.await_args.kwargs["headers"]


@pytest.mark.asyncio
async def test_openai_compatible_provider_implements_shared_runtime_contract() -> None:
    from runtime.models.messages import ModelRequest
    provider = OpenAICompatibleProvider(base_url="http://model.test/v1", api_key="", default_model="test-model")
    response = httpx.Response(200, json={"choices": [{"message": {"content": "Hello"}}]}, request=httpx.Request("POST", "http://model.test/v1/chat/completions"))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        result = await provider.generate(ModelRequest(prompt="Say hello"))
    assert result.content == "Hello"
    assert result.model == "test-model"
    assert result.provider == "openai-compatible"


def test_project_type_classifier_covers_requested_delivery_platforms() -> None:
    from src.company.project_types import classify_project_type, project_type_instructions
    assert classify_project_type("Habit Tracker", "Build a Flutter mobile app") == "mobile"
    assert classify_project_type("Invoice Tool", "Build a Windows desktop application") == "desktop"
    assert classify_project_type("Inventory API", "Build a REST API backend service") == "api"
    assert classify_project_type("Log Parser", "Create a command-line CLI tool") == "cli"
    assert classify_project_type("Date Utils", "Publish a reusable Python library") == "library"
    assert classify_project_type("Sales Dashboard", "Build a responsive web application") == "web"
    assert "Do not substitute a browser-only mockup" in project_type_instructions("mobile")
    from src.company.project_generator import OllamaProjectGenerator
    assert OllamaProjectGenerator._is_browser_mission("Build a Flutter mobile app") is False
    assert OllamaProjectGenerator._is_browser_mission("Build a Windows desktop application") is False
    assert OllamaProjectGenerator._is_browser_mission("Build a REST API backend service") is False
