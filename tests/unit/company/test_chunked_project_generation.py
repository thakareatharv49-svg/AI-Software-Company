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
                {"path": "tests/test_project.py", "purpose": "Mission-specific tests"},
                {"path": "app.js", "purpose": "Notes CRUD and search behavior"},
                {"path": "style.css", "purpose": "Responsive visual design"},
                {"path": "index.html", "purpose": "Accessible app entry point"},
            ]
        }),
        json.dumps({"content": "<!doctype html><html><head><title>Notes</title></head><body><script src=\"app.js\"></script><link rel=\"stylesheet\" href=\"style.css\"></body></html>"}),
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "function addNote(text) { return { text }; }"}),
        json.dumps({"content": "def add_note(text):\n    return {\"text\": text}\n\ndef test_create_task():\n    assert add_note(\"Plan\")[\"text\"] == \"Plan\"\n\ndef test_edit_task():\n    task = add_note(\"Plan\")\n    task[\"text\"] = \"Updated\"\n    assert task[\"text\"] == \"Updated\"\n\ndef test_delete_task():\n    tasks = [add_note(\"Plan\")]\n    tasks.remove(tasks[0])\n    assert tasks == []\n\ndef test_search_tasks():\n    tasks = [add_note(\"Plan\")]\n    assert [task for task in tasks if \"Plan\" in task[\"text\"]] == tasks\n"}),
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
    generated_paths = [
        payload["prompt"].split("File to generate: ", 1)[1].splitlines()[0]
        for payload in payloads[1:]
    ]
    assert generated_paths == [
        "index.html",
        "style.css",
        "app.js",
        "tests/test_project.py",
    ]


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
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "document.title = 'Recovered';"}),
        json.dumps({"content": "def test_generated_project_has_smoke_check():\n    assert True\n"}),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Large app",
        "Create, edit, delete, pin and search items in a responsive browser app.",
    )

    assert project.files["index.html"] == "<!doctype html><title>Recovered</title>"
    assert len(prompts) == 6
    assert "style.css" in project.files
    assert "app.js" in project.files
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
        "Large utility",
        "Create, edit, delete, pin and search items in a Python command-line utility.",
    )

    assert project.files["index.html"] == "<!doctype html><title>Recovered compact file</title>"
    assert [payload["options"]["num_predict"] for payload in payloads[:3]] == [
        3500,
        3500,
        5000,
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
        "Large utility",
        "Create, edit, delete, pin and search items in a Python command-line utility.",
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
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "document.title = 'Recovered';"}),
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
    assert len(prompts) == 6
    assert "style.css" in project.files
    assert "app.js" in project.files
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
        "Notes CLI",
        "Create, edit, delete, pin and search notes in a Python command-line utility.",
    )

    assert "index.html" in project.files
    assert "app.js" in project.files
    later_file_prompt = payloads[2]["prompt"]
    assert "FILE: index.html" in later_file_prompt
    assert '<button id="add-note">Add note</button>' in later_file_prompt
    assert '<script src="app.js"></script>' in later_file_prompt



@pytest.mark.asyncio
async def test_large_mission_rejects_manifest_that_exceeds_limit_after_required_files(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    manifest = {
        "files": [
            {"path": f"src/module_{index}.py", "purpose": f"Module {index}"}
            for index in range(40)
        ]
    }

    async def fake_call(payload):
        return json.dumps(manifest)

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="safe 40-file limit"):
        await generator._generate_large_mission(
            "Browser Dashboard",
            "Build a browser dashboard with search, filters, settings, and responsive layout.",
        )


def test_generic_application_missions_require_browser_assets_by_default() -> None:
    assert OllamaProjectGenerator._is_browser_mission(
        "Build a responsive habit application with streak tracking and reminders."
    )
    assert OllamaProjectGenerator._is_browser_mission(
        "Create a project management platform for a small team."
    )


def test_explicit_cli_and_api_missions_are_not_assumed_to_be_browser_apps() -> None:
    assert not OllamaProjectGenerator._is_browser_mission(
        "Build a Python CLI application that renames local files."
    )
    assert not OllamaProjectGenerator._is_browser_mission(
        "Create an API-only backend service for inventory."
    )


def test_generic_application_without_entry_point_fails_preview_validation() -> None:
    from src.company.project_generator import GeneratedProject

    with pytest.raises(RuntimeError, match="missing root index.html"):
        OllamaProjectGenerator._validate_mission_output(
            "Habit Application",
            "Build a responsive habit application with streak tracking.",
            GeneratedProject(
                files={"main.py": "def main():\n    return 1\n"},
                test_command=["python", "-m", "pytest", "-q"],
            ),
        )



@pytest.mark.asyncio
async def test_large_mission_stops_repeating_slow_non_json_file_failures(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({"files": [{"path": "index.html", "purpose": "App entry point"}]}),
        json.dumps({"content": "<!doctype html><html><head><title>Recovery</title></head><body></body></html>"}),
        RuntimeError("Ollama timed out"),
        RuntimeError("Ollama timed out again"),
    ]
    calls = 0

    async def fake_call(payload):
        nonlocal calls
        calls += 1
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="after 2 attempts: Ollama timed out again"):
        await generator._generate_large_mission(
            "Large app",
            "Create, edit, delete, pin and search items in a responsive browser app.",
        )

    assert calls == 4
    checkpoint = generator._checkpoint(
        "Large app",
        "Create, edit, delete, pin and search items in a responsive browser app.",
    ).load()
    assert checkpoint is not None
    assert checkpoint["files"]["index.html"].startswith("<!doctype html>")


@pytest.mark.asyncio
async def test_large_mission_replans_manifest_that_would_exceed_limit(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    oversized = {
        "files": [
            {"path": f"src/module_{index}.py", "purpose": f"Module {index}"}
            for index in range(40)
        ]
    }
    compact = {
        "files": [
            {"path": "index.html", "purpose": "Browser entry point"},
            {"path": "style.css", "purpose": "Responsive styling"},
            {"path": "app.js", "purpose": "Mission-specific interactions"},
            {"path": "tests/test_project.py", "purpose": "Behavior tests"},
        ]
    }
    responses = [
        json.dumps(oversized),
        json.dumps(compact),
        json.dumps({"content": "<!doctype html><html><head><title>Planner</title><link rel=\"stylesheet\" href=\"style.css\"></head><body><script src=\"app.js\"></script></body></html>"}),
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "function addTask(title) { return { title, completed: false }; }"}),
        json.dumps({"content": "def test_add_task_preserves_title():\n    task = {'title': 'Plan', 'completed': False}\n    assert task['title'] == 'Plan'\n"}),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Project Planner",
        "Create a project planner app with search, editing, task completion, and a responsive dashboard.",
    )

    assert len(prompts) == 6
    assert "Corrective retry" in prompts[1]
    assert set(project.files) == {
        "index.html", "style.css", "app.js", "tests/test_project.py"
    }

@pytest.mark.asyncio
async def test_large_mission_recovers_empty_but_valid_json_manifest(monkeypatch, tmp_path):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({"files": []}),
        json.dumps({
            "files": [
                {"path": "index.html", "purpose": "Browser application entry point"},
            ]
        }),
        json.dumps({
            "content": (
                '<!doctype html><html><head><link rel="stylesheet" href="style.css">'
                '</head><body><h1>Study Planner</h1><script src="app.js"></script></body></html>'
            )
        }),
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "function addStudySession(session) { return session; }"}),
        json.dumps({
            "content": (
                "def add_session(session):\n"
                "    return dict(session)\n\n"
                "def test_add_session_preserves_title():\n"
                "    assert add_session({'title': 'Math'})['title'] == 'Math'\n"
            )
        }),
    ]
    prompts = []

    async def fake_call(payload):
        prompts.append(payload["prompt"])
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    project = await generator._generate_large_mission(
        "Study Planner",
        "Create, edit, delete and search study sessions with a responsive browser dashboard.",
    )

    assert set(project.files) == {"index.html", "style.css", "app.js", "tests/test_project.py"}
    assert len(prompts) == 6
    assert "Structural recovery retry" in prompts[1]


@pytest.mark.asyncio
async def test_large_mission_fails_clearly_after_invalid_manifest_recovery(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    calls = 0

    async def fake_call(payload):
        nonlocal calls
        calls += 1
        return json.dumps({"files": [{"path": "../unsafe.py", "purpose": "Unsafe"}]})

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="after one structural recovery retry"):
        await generator._generate_large_mission(
            "Project Planner",
            "Create, edit, delete and search study sessions with a responsive dashboard.",
        )

    assert calls == 2


@pytest.mark.asyncio
async def test_test_file_prompt_prioritizes_implementation_over_large_stylesheet(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({
            "files": [
                {"path": "index.html", "purpose": "App entry point"},
                {"path": "style.css", "purpose": "Visual design"},
                {"path": "app.js", "purpose": "Core behavior"},
                {"path": "tests/test_project.py", "purpose": "Behavior tests"},
            ]
        }),
        json.dumps({
            "content": (
                '<!doctype html><html><head><link rel="stylesheet" href="style.css">'
                '</head><body><script src="app.js"></script></body></html>'
            )
        }),
        json.dumps({"content": "/*" + ("x" * 5900) + "*/"}),
        json.dumps({"content": "function addNote(title) { return { title }; }"}),
        json.dumps({
            "content": (
                "def test_note_title_is_preserved():\n"
                "    note = {'title': 'Plan'}\n"
                "    assert note['title'] == 'Plan'\n"
            )
        }),
    ]
    payloads = []

    async def fake_call(payload):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    await generator._generate_large_mission(
        "Project Planner",
        "Create and search project notes in a responsive browser app.",
    )

    test_prompt = payloads[-1]["prompt"]
    assert "FILE: app.js" in test_prompt
    assert "function addNote(title)" in test_prompt


@pytest.mark.asyncio
async def test_large_mission_uses_configured_file_budget_in_manifest_prompt(monkeypatch, tmp_path):
    generator = OllamaProjectGenerator(
        checkpoint_dir=tmp_path,
        max_generated_project_files=72,
    )
    captured = []
    responses = [
        json.dumps({"files": [{"path": "index.html", "purpose": "App entry point"}]}),
        json.dumps({"content": "<!doctype html><title>Budget test</title>"}),
        json.dumps({"content": "body { font-family: sans-serif; }"}),
        json.dumps({"content": "document.title = 'Budget test';"}),
        json.dumps({"content": "def test_product_has_title():\n    assert 'Budget test' in '<title>Budget test</title>'\n"}),
    ]

    async def fake_call(payload):
        captured.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    await generator._generate_large_mission(
        "Budget test app",
        "Create, edit, delete and search records in a responsive browser app.",
    )

    assert "no more than 72 files" in captured[0]["prompt"]


@pytest.mark.asyncio
async def test_large_mission_rejects_invalid_compact_manifest(monkeypatch, tmp_path) -> None:
    generator = OllamaProjectGenerator(
        checkpoint_dir=tmp_path,
        max_generated_project_files=5,
    )
    initial_manifest = {
        "files": [
            {"path": f"module_{index}.py", "purpose": f"Module {index}"}
            for index in range(6)
        ]
    }
    # The compact response is structurally valid and fits the nominal count,
    # but leaves no room for mandatory browser assets. It must not replace the
    # original plan.
    compact_manifest = {
        "files": [
            {"path": "index.html", "purpose": "Browser entry"},
            {"path": "tests/test_project.py", "purpose": "Behavior tests"},
            {"path": "src/main.py", "purpose": "Application entry"},
            {"path": "README.md", "purpose": "Project documentation"},
        ]
    }
    responses = [json.dumps(initial_manifest), json.dumps(compact_manifest)]

    async def fake_call(payload):
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    with pytest.raises(RuntimeError, match="safe limit is 5"):
        await generator._generate_large_mission(
            "Browser project platform",
            "Create a browser project platform with a dashboard and analytics.",
        )

@pytest.mark.asyncio
async def test_large_generation_keeps_file_context_bounded_and_dependency_first(
    monkeypatch, tmp_path
):
    generator = OllamaProjectGenerator(checkpoint_dir=tmp_path)
    responses = [
        json.dumps({
            "files": [
                {"path": "index.html", "purpose": "App entry point"},
                {"path": "style.css", "purpose": "Visual styling"},
                {
                    "path": "app.js",
                    "purpose": "Interactive behavior",
                    "depends_on": ["index.html"],
                },
                {"path": "tests/test_project.py", "purpose": "Behavior tests"},
            ]
        }),
        json.dumps({"content": "<!doctype html><title>Context</title>"}),
        json.dumps({"content": "body { color: black; }"}),
        json.dumps({"content": "function runApp() { return true; }"}),
        json.dumps({"content": "def add_note(text):\\n    return {'text': text}\\n\\ndef test_add_note_preserves_text():\\n    assert add_note('Plan')['text'] == 'Plan'\\n"}),
    ]
    payloads = []

    async def fake_call(payload):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(generator, "_call", fake_call)
    await generator._generate_large_mission(
        "Context planner",
        "Create, edit, delete and search records in a responsive browser app.",
    )

    file_prompts = [
        payload["prompt"] for payload in payloads
        if "File to generate: " in payload["prompt"]
    ]
    assert file_prompts
    assert all(len(prompt) < 12_000 for prompt in file_prompts)
    app_prompt = next(
        prompt for prompt in file_prompts
        if "File to generate: app.js" in prompt
    )
    assert "FILE: index.html" in app_prompt
    assert "- index.html" in app_prompt
    assert "- index.html: App entry point" not in app_prompt
    assert "- style.css: Visual styling" not in app_prompt
