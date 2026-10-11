from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class GenerationCheckpointStore:
    """Atomically persist generated files so interrupted missions can resume."""

    def __init__(self, directory: str | Path, *, key: str) -> None:
        self.directory = Path(directory)
        self.key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        self.path = self.directory / f"{self.key_hash}.json"

    def load(self) -> dict[str, Any] | None:
        """Return a valid checkpoint, ignoring corrupt or incompatible files."""
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != 1
            or payload.get("key_hash") != self.key_hash
            or not isinstance(payload.get("manifest"), list)
            or not isinstance(payload.get("files"), dict)
        ):
            return None
        return payload

    def compatible_files(
        self, manifest: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Return cached files only when their manifest contract is unchanged.

        A file generated for a different purpose or dependency contract may no
        longer be compatible with the current plan, even if its path is reused.
        """
        payload = self.load()
        if payload is None:
            return {}

        def contract(item: object) -> tuple[str, str, tuple[str, ...]] | None:
            if not isinstance(item, dict):
                return None
            path = item.get("path")
            purpose = item.get("purpose")
            dependencies = item.get("depends_on", [])
            if (
                not isinstance(path, str)
                or not path.strip()
                or not isinstance(purpose, str)
                or not isinstance(dependencies, list)
                or any(not isinstance(dep, str) for dep in dependencies)
            ):
                return None
            normalized_path = path.replace("\\", "/").strip().casefold()
            normalized_dependencies = tuple(sorted(
                dep.replace("\\", "/").strip().casefold()
                for dep in dependencies
            ))
            return normalized_path, purpose.strip(), normalized_dependencies

        previous = {
            key: item.get("path")
            for item in payload["manifest"]
            if (key := contract(item)) is not None
        }
        compatible_paths = {
            item.get("path")
            for item in manifest
            if (key := contract(item)) is not None and key in previous
        }
        cached = payload["files"]
        return {
            path: content
            for path, content in cached.items()
            if path in compatible_paths and isinstance(content, str)
        }

    def save(self, *, manifest: list[dict[str, str]], files: dict[str, str]) -> None:
        """Atomically replace the checkpoint after each completed file."""
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "key_hash": self.key_hash,
            "manifest": manifest,
            "files": files,
        }
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.directory,
                prefix=f".{self.key_hash}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = temporary.name
                json.dump(payload, temporary, ensure_ascii=False)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)

    def clear(self) -> None:
        """Remove a checkpoint after the generated project passes validation."""
        self.path.unlink(missing_ok=True)
