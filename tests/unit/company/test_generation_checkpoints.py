import json

import pytest

from src.company.generation_checkpoints import GenerationCheckpointStore
from src.company.project_generator import OllamaProjectGenerator


def test_checkpoint_round_trips_and_is_scoped_to_mission(tmp_path) -> None:
    store = GenerationCheckpointStore(tmp_path, key="Notes App\0Build notes")
    store.save(
        manifest=[{"path": "index.html", "purpose": "entry point"}],
        files={"index.html": "<!doctype html>"},
    )

    assert store.load() == {
        "schema_version": 1,
        "key_hash": store.key_hash,
        "manifest": [{"path": "index.html", "purpose": "entry point"}],
        "files": {"index.html": "<!doctype html>"},
    }
    assert GenerationCheckpointStore(tmp_path, key="Different mission").load() is None


def test_corrupt_checkpoint_is_ignored(tmp_path) -> None:
    store = GenerationCheckpointStore(tmp_path, key="mission")
    store.path.write_text("{not json", encoding="utf-8")

    assert store.load() is None


def test_clear_removes_checkpoint(tmp_path) -> None:
    store = GenerationCheckpointStore(tmp_path, key="mission")
    store.save(manifest=[], files={})
    store.clear()

    assert store.load() is None


@pytest.mark.asyncio
async def test_large_mission_resumes_completed_files_after_interruption(
    tmp_path, monkeypatch
) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({
            "files": [
                {"path": "index.html", "purpose": "App entry point"},
                {"path": "app.js", "purpose": "Core behavior"},
            ]
        }),
        json.dumps({"content": "<!doctype html><title>Notes</title>"}),
        "invalid JSON",
        "invalid JSON",
        "invalid JSON",
        json.dumps({"content": "function addNote(text) { return { text }; }"}),
    ]
    prompts: list[str] = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="Failed to generate 'app.js'"):
        await generator._generate_large_mission(
            "Notes App",
            "Create, edit, delete, pin and search notes with responsive local storage.",
        )

    resumed = await generator._generate_large_mission(
        "Notes App",
        "Create, edit, delete, pin and search notes with responsive local storage.",
    )

    assert resumed.files["index.html"] == "<!doctype html><title>Notes</title>"
    assert resumed.files["app.js"] == "function addNote(text) { return { text }; }"
    assert len(prompts) == 6
    assert "Plan a small, complete software product" not in prompts[5]
