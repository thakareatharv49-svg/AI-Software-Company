from __future__ import annotations

import subprocess

import pytest

from src.company.project_generator import OllamaProjectGenerator


def test_javascript_validation_skips_when_node_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("src.company.project_generator.shutil.which", lambda _: None)

    OllamaProjectGenerator._validate_javascript_syntax({"app.js": "const = ;"})


def test_javascript_validation_runs_node_syntax_check(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr("src.company.project_generator.shutil.which", lambda _: "/usr/bin/node")

    def fake_run(command, **kwargs):
        calls.append(command)
        assert kwargs["timeout"] == 10
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("src.company.project_generator.subprocess.run", fake_run)

    OllamaProjectGenerator._validate_javascript_syntax(
        {"app.js": "function add(a, b) { return a + b; }"}
    )

    assert len(calls) == 1
    assert calls[0][:2] == ["/usr/bin/node", "--check"]


def test_javascript_syntax_error_is_actionable(monkeypatch) -> None:
    monkeypatch.setattr("src.company.project_generator.shutil.which", lambda _: "/usr/bin/node")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 1, "", "SyntaxError: Unexpected token"
        )

    monkeypatch.setattr("src.company.project_generator.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="syntax error in 'app.js'.*Unexpected token"):
        OllamaProjectGenerator._validate_javascript_syntax({"app.js": "const = ;"})


def test_non_javascript_files_do_not_run_node(monkeypatch) -> None:
    def unexpected_run(*args, **kwargs):
        raise AssertionError("Node should not be invoked when no JS files exist")

    monkeypatch.setattr("src.company.project_generator.shutil.which", lambda _: "/usr/bin/node")
    monkeypatch.setattr("src.company.project_generator.subprocess.run", unexpected_run)

    OllamaProjectGenerator._validate_javascript_syntax(
        {"index.html": "<h1>Product</h1>", "style.css": "h1 { color: red; }"}
    )
