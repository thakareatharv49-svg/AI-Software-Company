import json

import pytest

from src.company.project_generator import OllamaProjectGenerator


def test_large_mission_uses_chunked_generation() -> None:
    assert OllamaProjectGenerator._is_large_mission(
        "Notes App",
        "Create, edit, delete, pin, search and filter notes with responsive local storage.",
    )


def test_small_mission_keeps_single_pass_generation() -> None:
    assert not OllamaProjectGenerator._is_large_mission(
        "Tiny utility",
        "Print one greeting.",
    )


@pytest.mark.asyncio
async def test_large_mission_generates_each_file_independently(monkeypatch) -> None:
    generator = OllamaProjectGenerator()
    responses = [
        json.dumps({
            "files": [
                {"path": "index.html", "purpose": "Accessible app entry point"},
                {"path": "style.css", "purpose": "Responsive visual design"},
                {"path": "app.js", "purpose": "Notes CRUD and search behavior"},
                {"path": "tests/test_project.py", "purpose": "Mission-specific tests"},
            ]
        }),
        json.dumps({"content": "<!doctype html><html><head><title>Notes</title></head><body><script src=\"app.js\"></script><link rel=\"stylesheet\" href=\"style.css\"></body></html>"}),
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "function addNote(text) { return { text }; }"}),
        json.dumps({"content": "def add_note(text):\n    return {\"text\": text}\n\ndef test_add_note_preserves_content():\n    assert add_note(\"Plan\")[\"text\"] == \"Plan\"\n"}),
    ]
    payloads = []

    async def fake_call(payload):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    # Use a different large browser product here: Notes App missions now take
    # the deterministic implementation path and should not exercise Ollama.
    project = await generator.generate(
        "Project Planner",
        "Create, edit, delete and search project tasks in a responsive browser app.",
    )

    assert set(project.files) == {
        "index.html",
        "style.css",
        "app.js",
        "tests/test_project.py",
    }
    assert len(payloads) == 5
    assert project.test_command == ["python", "-m", "pytest", "-q"]
    assert all("num_predict" in payload["options"] for payload in payloads)


@pytest.mark.asyncio
async def test_large_mission_rejects_unsafe_manifest_paths(monkeypatch) -> None:
    generator = OllamaProjectGenerator()

    async def fake_call(payload):
        return json.dumps({"files": [{"path": "../outside.txt", "purpose": "unsafe"}]})

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="Unsafe path"):
        await generator._generate_large_mission("Notes App", "Create, edit, delete, pin, search notes.")


@pytest.mark.asyncio
async def test_large_mission_retries_only_the_failed_file(monkeypatch, tmp_path) -> None:
    # Use a fresh checkpoint store so prior local test runs cannot skip mocked calls.
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({"files": [{"path": "index.html", "purpose": "App entry point"}]}),
        "not valid JSON",
        json.dumps({"content": "<!doctype html><title>Recovered</title>"}),
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Large app",
        "Create, edit, delete, pin and search items with responsive UI.",
    )

    assert project.files["index.html"] == "<!doctype html><title>Recovered</title>"
    assert len(prompts) == 4
    assert "tests/test_project.py" in project.files
    assert "Previous attempt failed with this error" in prompts[2]


@pytest.mark.asyncio
async def test_large_mission_adapts_file_token_budget_after_invalid_json(monkeypatch, tmp_path):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({"files": [{"path": "index.html", "purpose": "App entry point"}]}),
        "not valid JSON",
        json.dumps({"content": "<!doctype html><title>Recovered compact file</title>"}),
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    payloads = []

    async def fake_call(payload):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Large app",
        "Create, edit, delete, pin and search items with responsive UI.",
    )

    assert project.files["index.html"] == "<!doctype html><title>Recovered compact file</title>"
    assert [payload["options"]["num_predict"] for payload in payloads[:3]] == [
        1800,
        3500,
        2400,
    ]
    assert len(payloads) == 4
    assert "tests/test_project.py" in project.files
    assert "Adaptive recovery attempt 2" in payloads[2]["prompt"]


@pytest.mark.asyncio
async def test_large_mission_retries_invalid_file_manifest(monkeypatch, tmp_path):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        "not valid JSON",
        json.dumps({"files": [{"path": "index.html", "purpose": "App entry point"}]}),
        json.dumps({"content": "<!doctype html><title>Manifest recovered</title>"}),
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    payloads = []

    async def fake_call(payload):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Large app",
        "Create, edit, delete, pin and search items with responsive UI.",
    )

    assert project.files["index.html"] == "<!doctype html><title>Manifest recovered</title>"
    assert len(payloads) == 4
    assert "tests/test_project.py" in project.files
    assert "Corrective retry" in payloads[1]["prompt"]


@pytest.mark.asyncio
async def test_large_mission_retries_transient_manifest_request_failure(monkeypatch, tmp_path):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    manifest = json.dumps({
        "files": [{"path": "index.html", "purpose": "Browser app entry point"}]
    })
    responses = [
        RuntimeError("Could not reach Ollama"),
        manifest,
        json.dumps({"content": "<!doctype html><title>Recovered</title>"}),
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Project Planner",
        "Create, edit, delete and search project tasks with a responsive dashboard.",
    )

    assert project.files["index.html"] == "<!doctype html><title>Recovered</title>"
    assert len(prompts) == 4
    assert "tests/test_project.py" in project.files
    assert "Recovery retry" in prompts[1]
    assert "Could not reach Ollama" not in prompts[1]


@pytest.mark.asyncio
async def test_large_mission_reports_exhausted_manifest_transport_retries(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    calls = 0

    async def fake_call(payload):
        nonlocal calls
        calls += 1
        raise RuntimeError("Ollama timed out")

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="could not generate the project file plan") as exc:
        await generator._generate_large_mission(
            "Project Planner",
            "Create, edit, delete and search project tasks with a responsive dashboard.",
        )

    assert calls == 2
    assert "Ollama timed out" in str(exc.value)


@pytest.mark.asyncio
async def test_later_file_prompt_includes_actual_previously_generated_source(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({
            "files": [
                {"path": "index.html", "purpose": "Notes app interface and controls"},
                {"path": "app.js", "purpose": "Notes interactions and state"},
            ]
        }),
        json.dumps({
            "content": (
                '<!doctype html><html><head><title>Notes</title></head><body>'
                '<button id="add-note">Add note</button>'
                '<script src="app.js"></script></body></html>'
            )
        }),
        json.dumps({
            "content": (
                'document.querySelector("#add-note")?.addEventListener("click", () => {});'
            )
        }),
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    payloads = []

    async def fake_call(payload):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Notes App",
        "Create, edit, delete, pin and search notes with responsive local storage.",
    )

    assert "index.html" in project.files
    assert "app.js" in project.files
    later_file_prompt = payloads[2]["prompt"]
    assert "FILE: index.html" in later_file_prompt
    assert '<button id="add-note">Add note</button>' in later_file_prompt
    assert '<script src="app.js"></script>' in later_file_prompt
