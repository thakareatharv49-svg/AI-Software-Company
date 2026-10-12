import asyncio
import time
from types import SimpleNamespace

from src.company.autonomous_factory_runner import FactoryAutonomousRunner
from src.company.project_generator import GeneratedProject, OllamaProjectGenerator


def test_generator_returns_aggregated_model_usage(tmp_path, monkeypatch):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)

    async def fake_generation(name, objective):
        generator._generation_model_calls = 3
        generator._generation_prompt_tokens = 1200
        generator._generation_output_tokens = 450
        return GeneratedProject(
            files={"index.html": "<h1>Demo</h1>"},
            test_command=["python", "-m", "pytest"],
        )

    monkeypatch.setattr(generator, "_generate_with_budget", fake_generation)
    generated = asyncio.run(generator.generate("Demo", "Build a demo"))

    assert generated.model_calls == 3
    assert generated.prompt_tokens == 1200
    assert generated.generated_tokens == 450
    assert generated.duration_ms >= 0
    assert generator._generation_deadline is None


def test_factory_runner_copies_usage_metrics_to_durable_plan():
    request = SimpleNamespace(
        generation_model_calls=7,
        generation_duration_ms=12345,
        generation_prompt_tokens=9000,
        generation_output_tokens=2100,
    )

    updates = FactoryAutonomousRunner._generation_metrics_updates(request)

    assert updates == {
        "generation_model_calls": 7,
        "generation_duration_ms": 12345,
        "generation_prompt_tokens": 9000,
        "generation_output_tokens": 2100,
    }


def test_factory_runner_defaults_metrics_for_legacy_request_builders():
    updates = FactoryAutonomousRunner._generation_metrics_updates(SimpleNamespace())

    assert updates == {
        "generation_model_calls": 0,
        "generation_duration_ms": 0,
        "generation_prompt_tokens": 0,
        "generation_output_tokens": 0,
    }


def test_factory_runner_clamps_invalid_negative_usage_metrics():
    updates = FactoryAutonomousRunner._generation_metrics_updates(
        SimpleNamespace(
            generation_model_calls=-1,
            generation_duration_ms=-2,
            generation_prompt_tokens=-3,
            generation_output_tokens=-4,
        )
    )

    assert all(value == 0 for value in updates.values())



def test_ollama_response_token_counts_are_aggregated(tmp_path, monkeypatch):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    generator._generation_deadline = time.monotonic() + 60

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": '{"files": {}, "test_command": []}',
                "prompt_eval_count": 123,
                "eval_count": 45,
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr("src.company.project_generator.httpx.AsyncClient", FakeClient)

    result = asyncio.run(generator._call({"model": "test-model", "prompt": "test"}))

    assert result == '{"files": {}, "test_command": []}'
    assert generator._generation_model_calls == 1
    assert generator._generation_prompt_tokens == 123
    assert generator._generation_output_tokens == 45
