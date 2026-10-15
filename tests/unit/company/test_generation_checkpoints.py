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


def test_resumed_checkpoint_files_reject_broken_python_and_json(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)

    assert not generator._checkpoint_file_is_reusable("src/broken.py", "def broken(:\n    pass")
    assert not generator._checkpoint_file_is_reusable("config.json", '{"enabled":')
    assert not generator._checkpoint_file_is_reusable("src/empty.py", "  \n")
    assert generator._checkpoint_file_is_reusable("src/valid.py", "def ready():\n    return True\n")
    assert generator._checkpoint_file_is_reusable("config.json", '{"enabled": true}')



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
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    prompts: list[str] = []
    payloads: list[dict] = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="Failed to generate 'app.js'"):
        await generator._generate_large_mission(
            "Notes CLI",
            "Create, edit, delete, pin and search notes in a Python command-line utility.",
        )

    resumed = await generator._generate_large_mission(
        "Notes CLI",
        "Create, edit, delete, pin and search notes in a Python command-line utility.",
    )

    assert resumed.files["index.html"] == "<!doctype html><title>Notes</title>"
    assert resumed.files["app.js"] == "function addNote(text) { return { text }; }"
    assert "tests/test_project.py" in resumed.files
    assert len(prompts) == 7
    assert "Plan a small, complete software product" not in prompts[5]
    app_js_budgets = [
        payload["options"]["num_predict"]
        for payload in payloads
        if "File to generate: app.js" in payload["prompt"]
    ]
    assert app_js_budgets == [3500, 5000, 6500, 3500]


def test_checkpoint_reuses_only_files_with_matching_manifest_contract(tmp_path) -> None:
    store = GenerationCheckpointStore(tmp_path, key="mission")
    old_manifest = [
        {"path": "src/core.py", "purpose": "Core logic", "depends_on": []},
        {"path": "src/ui.py", "purpose": "UI", "depends_on": ["src/core.py"]},
        {"path": "tests/test_core.py", "purpose": "Core tests", "depends_on": ["src/core.py"]},
    ]
    store.save(
        manifest=old_manifest,
        files={
            "src/core.py": "old core",
            "src/ui.py": "old ui",
            "tests/test_core.py": "old tests",
        },
    )

    current_manifest = [
        {"path": "src/core.py", "purpose": "Core logic", "depends_on": []},
        {"path": "src/ui.py", "purpose": "UI", "depends_on": ["src/new_core.py"]},
        {"path": "tests/test_core.py", "purpose": "Tests for new core contract", "depends_on": ["src/core.py"]},
        {"path": "src/new_core.py", "purpose": "New core module", "depends_on": []},
    ]

    assert store.compatible_files(current_manifest) == {
        "src/core.py": "old core"
    }


def test_checkpoint_dependency_order_does_not_invalidate_same_contract(tmp_path) -> None:
    store = GenerationCheckpointStore(tmp_path, key="mission")
    store.save(
        manifest=[{
            "path": "src/ui.py",
            "purpose": "UI",
            "depends_on": ["src/core.py", "src/theme.py"],
        }],
        files={"src/ui.py": "cached ui"},
    )

    assert store.compatible_files([{
        "path": "src/ui.py",
        "purpose": "UI",
        "depends_on": ["src/theme.py", "src/core.py"],
    }]) == {"src/ui.py": "cached ui"}


def test_checkpoint_invalidates_transitive_consumers_of_changed_dependency(tmp_path) -> None:
    store = GenerationCheckpointStore(tmp_path, key="dependency graph")
    store.save(
        manifest=[
            {"path": "src/core.py", "purpose": "Core v1", "depends_on": []},
            {"path": "src/service.py", "purpose": "Service", "depends_on": ["src/core.py"]},
            {"path": "src/ui.py", "purpose": "UI", "depends_on": ["src/service.py"]},
        ],
        files={
            "src/core.py": "old core",
            "src/service.py": "old service",
            "src/ui.py": "old ui",
        },
    )

    current_manifest = [
        {"path": "src/core.py", "purpose": "Core v2", "depends_on": []},
        {"path": "src/service.py", "purpose": "Service", "depends_on": ["src/core.py"]},
        {"path": "src/ui.py", "purpose": "UI", "depends_on": ["src/service.py"]},
    ]

    assert store.compatible_files(current_manifest) == {}


def test_automatic_retry_feedback_reuses_original_mission_checkpoint(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    objective = "Build a clinic management system with appointments and patient records"
    retry_objective = (
        objective
        + "\n\nAUTOMATIC RECOVERY FEEDBACK FROM THE PREVIOUS ATTEMPT:\n"
        + "QA failed: appointment validation is missing"
    )

    original = generator._checkpoint("Clinic Management System", objective)
    retried = generator._checkpoint("Clinic Management System", retry_objective)

    assert retried.key_hash == original.key_hash


def test_owner_requested_revision_uses_a_distinct_checkpoint(tmp_path) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    objective = "Build a clinic management system"
    revision = objective + "\n\nOWNER-REQUESTED REVISION FEEDBACK:\nAdd billing"

    original = generator._checkpoint("Clinic Management System", objective)
    revised = generator._checkpoint("Clinic Management System", revision)

    assert revised.key_hash != original.key_hash


@pytest.mark.asyncio
async def test_invalid_generated_python_is_retried_before_checkpointing(
    tmp_path, monkeypatch
) -> None:
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({
            "files": [
                {"path": "src/library.py", "purpose": "Public library functions"},
                {"path": "tests/test_library.py", "purpose": "Behavioral tests"},
            ]
        }),
        json.dumps({"content": "def broken(:\n    return 1"}),
        json.dumps({"content": "def add(left: int, right: int) -> int:\n    return left + right\n"}),
        json.dumps({"content": "from src.library import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"}),
    ]
    prompts: list[str] = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    generated = await generator._generate_large_mission(
        "Reusable Python Library",
        "Create a Python library that exposes an add function and tests.",
    )

    assert generated.files["src/library.py"] == (
        "def add(left: int, right: int) -> int:\n    return left + right\n"
    )
    assert len(prompts) == 4
    assert "generated Python has a syntax error" in prompts[2]
    checkpoint = generator._checkpoint(
        "Reusable Python Library",
        "Create a Python library that exposes an add function and tests.",
    ).load()
    assert checkpoint is not None
    assert checkpoint["files"]["src/library.py"] == generated.files["src/library.py"]
