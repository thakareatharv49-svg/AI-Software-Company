import math

import pytest
from pydantic import ValidationError

from config.settings import Settings


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ollama", "ollama"),
        (" OPENAI-COMPATIBLE ", "openai-compatible"),
        ("OpenAI_Compatible", "openai_compatible"),
    ],
)
def test_factory_provider_name_is_normalized(value: str, expected: str) -> None:
    assert make_settings(factory_model_provider=value).factory_model_provider == expected


def test_unsupported_factory_provider_fails_during_configuration() -> None:
    with pytest.raises(ValidationError, match="FACTORY_MODEL_PROVIDER"):
        make_settings(factory_model_provider="unknown-provider")


@pytest.mark.parametrize("field", ["ollama_timeout", "openai_compatible_timeout"])
@pytest.mark.parametrize("value", [0, -1, math.inf, -math.inf, math.nan])
def test_provider_timeouts_must_be_finite_and_positive(field: str, value: float) -> None:
    with pytest.raises(ValidationError, match="finite positive"):
        make_settings(**{field: value})


@pytest.mark.parametrize("field", ["ollama_model", "openai_compatible_model"])
def test_provider_model_names_must_not_be_blank(field: str) -> None:
    with pytest.raises(ValidationError, match="model name cannot be empty"):
        make_settings(**{field: "   "})


@pytest.mark.parametrize("field", ["ollama_base_url", "openai_compatible_base_url"])
@pytest.mark.parametrize(
    "value",
    ["", "file:///tmp/model", "ftp://model.test", "http://user:pass@model.test/v1"],
)
def test_provider_urls_must_be_http_urls_without_embedded_credentials(
    field: str, value: str
) -> None:
    with pytest.raises(ValidationError, match="HTTP\(S\) URL"):
        make_settings(**{field: value})


def test_default_provider_settings_remain_valid() -> None:
    settings = make_settings()
    assert settings.factory_model_provider == "ollama"
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.openai_compatible_base_url == "https://api.openai.com/v1"
