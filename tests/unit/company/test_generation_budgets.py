import asyncio
import time

import pytest

from src.company.project_generator import GeneratedProject, OllamaProjectGenerator
from src.config.settings import settings


def test_generation_budget_wraps_one_mission_and_resets_afterward(tmp_path, monkeypatch):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    observed = {}

    async def fake_generation(name, objective):
        observed["deadline"] = generator._generation_deadline
        observed["calls"] = generator._generation_model_calls
        return GeneratedProject(files={"index.html": "<h1>ok</h1>"}, test_command=["python", "-m", "pytest"])

    monkeypatch.setattr(generator, "_generate_with_budget", fake_generation)
    result = asyncio.run(generator.generate("Demo", "Build a demo"))

    assert result.files["index.html"] == "<h1>ok</h1>"
    assert observed["deadline"] is not None
    assert observed["deadline"] > time.monotonic()
    assert observed["calls"] == 0
    assert generator._generation_deadline is None


def test_model_call_is_rejected_after_generation_deadline(tmp_path):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    generator._generation_deadline = time.monotonic() - 1

    with pytest.raises(RuntimeError, match="hard time budget"):
        asyncio.run(generator._call({"model": "unused", "prompt": "unused"}))


def test_model_call_is_rejected_after_call_budget_is_exhausted(tmp_path):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    generator._generation_deadline = time.monotonic() + 60
    generator._generation_model_calls = settings.factory_max_generation_model_calls

    with pytest.raises(RuntimeError, match="hard model-call limit"):
        asyncio.run(generator._call({"model": "unused", "prompt": "unused"}))
