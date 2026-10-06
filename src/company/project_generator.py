from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath

import httpx

from src.config.settings import settings


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    files: dict[str, str]
    test_command: list[str]


class OllamaProjectGenerator:
    """Generate a small, runnable project from a company mission."""

    async def generate(self, name: str, objective: str) -> GeneratedProject:
        prompt = f"""Build a small, runnable software project for this mission.

Project: {name}
Objective: {objective}

Return ONLY valid JSON with this shape:
{{"files": {{"relative/path": "complete file contents"}},
 "test_command": ["python", "-m", "pytest", "-q"]}}

Rules:
- Generate a complete runnable implementation, not a plan.
- Include automated tests under tests/.
- Keep the project small enough to run locally.
- Use Python standard library where practical.
- Never use absolute paths.
- Do not include secrets, credentials, shell commands, or network calls in generated source.
- File keys must be plain relative filenames only (for example tests/test_calculator.py).
- Never put line numbers, source excerpts, colons, or annotations in file keys.
- The test command must run from the project root.
"""
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "files": {"type": "object", "additionalProperties": {"type": "string"}},
                    "test_command": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["files", "test_command"],
            },
            "keep_alive": "10m",
            "options": {"temperature": 0.1, "num_predict": 768},
        }
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        try:
            result = json.loads(data.get("response", ""))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned invalid project JSON") from exc

        raw_files = result.get("files")
        if not isinstance(raw_files, dict) or not raw_files:
            raise RuntimeError("Ollama returned no project files")

        files: dict[str, str] = {}
        for raw_path, content in raw_files.items():
            raw_path_text = str(raw_path).strip().replace("\\", "/")
            path = PurePosixPath(raw_path_text)
            if (
                path.is_absolute()
                or ".." in path.parts
                or ":" in raw_path_text
                or "\n" in raw_path_text
            ):
                raise RuntimeError(f"Unsafe generated path: {raw_path}")
            if not content or len(str(content).encode("utf-8")) > 2_000_000:
                raise RuntimeError(f"Invalid generated file: {raw_path}")
            files[str(path)] = str(content)

        if not any(path.startswith("tests/") for path in files):
            raise RuntimeError("Generated project must include tests")

        command = result.get("test_command", ["python", "-m", "pytest", "-q"])
        if not isinstance(command, list) or not command:
            raise RuntimeError("Generated test command is invalid")

        return GeneratedProject(files=files, test_command=[str(item) for item in command])
