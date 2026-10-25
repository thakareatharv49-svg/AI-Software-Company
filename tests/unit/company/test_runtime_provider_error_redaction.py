from unittest.mock import AsyncMock, patch

import httpx
import pytest

from config.settings import settings
from src.company.project_generator import OllamaProjectGenerator


@pytest.mark.asyncio
async def test_project_generator_redacts_upstream_http_error_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "factory_model_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.test")
    monkeypatch.setattr(settings, "ollama_timeout", 1.0)
    generator = OllamaProjectGenerator()
    response = httpx.Response(
        401,
        text="Authorization failed for token TOP-SECRET-EXAMPLE",
        request=httpx.Request("POST", "http://ollama.test/api/generate"),
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = response
        with pytest.raises(RuntimeError, match="HTTP 401") as error:
            await generator._call({"model": "test-model", "prompt": "hello"})
    assert "TOP-SECRET-EXAMPLE" not in str(error.value)
    assert "Authorization failed" not in str(error.value)


@pytest.mark.asyncio
async def test_project_generator_redacts_provider_url_and_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "factory_model_provider", "ollama")
    monkeypatch.setattr(
        settings, "ollama_base_url", "http://private-user:private-pass@ollama.test"
    )
    monkeypatch.setattr(settings, "ollama_timeout", 1.0)
    generator = OllamaProjectGenerator()
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("transport failed at private-pass"),
    ):
        with pytest.raises(RuntimeError, match="Could not reach the Ollama provider") as error:
            await generator._call({"model": "test-model", "prompt": "hello"})
    assert "private-user" not in str(error.value)
    assert "private-pass" not in str(error.value)
    assert "http://" not in str(error.value)
