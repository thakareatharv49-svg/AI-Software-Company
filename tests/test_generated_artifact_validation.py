from __future__ import annotations

import pytest

from src.company.autonomous_factory_runner import FactoryAutonomousRunner


@pytest.mark.parametrize(
    "files",
    [
        {},
        {"index.html": ""},
        {"index.html": "  ", "app.js": "\n"},
    ],
)
def test_generated_artifacts_reject_empty_file_sets(files: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="no files|all empty"):
        FactoryAutonomousRunner._validate_generated_files(files)


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "src/../../outside.txt",
        r"..\\outside.txt",
        r"C:\\outside.txt",
        "/outside.txt",
    ],
)
def test_generated_artifacts_reject_unsafe_paths(path: str) -> None:
    with pytest.raises(ValueError, match="unsafe path"):
        FactoryAutonomousRunner._validate_generated_files({path: "content"})


def test_generated_artifacts_accept_nonempty_relative_files() -> None:
    FactoryAutonomousRunner._validate_generated_files(
        {
            "index.html": "<!doctype html><title>App</title>",
            "assets/app.js": "console.log('ready')",
        }
    )
