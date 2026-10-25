import json

import pytest

from src.company.project_generator import OllamaProjectGenerator


@pytest.mark.parametrize("response", ["[]", "null", "42", '"text"'])
def test_project_parser_rejects_non_object_json(response: str) -> None:
    with pytest.raises(RuntimeError, match="invalid project JSON object"):
        OllamaProjectGenerator()._parse(response)


def test_project_parser_rejects_object_without_files() -> None:
    with pytest.raises(RuntimeError, match="no project files"):
        OllamaProjectGenerator()._parse(json.dumps({"message": "done"}))


def test_project_parser_accepts_valid_structured_project() -> None:
    project = OllamaProjectGenerator()._parse(
        json.dumps(
            {
                "files": {
                    "index.html": "<!doctype html><title>Sample</title>",
                    "app.js": "document.title = 'Sample';",
                },
                "test_command": ["python", "-m", "pytest", "-q"],
            }
        )
    )
    assert project.files["index.html"].startswith("<!doctype html>")
    assert project.files["app.js"] == "document.title = 'Sample';"


def test_project_parser_rejects_invalid_json_without_object_boundary() -> None:
    with pytest.raises(RuntimeError, match="invalid project JSON"):
        OllamaProjectGenerator()._parse("not-json")
