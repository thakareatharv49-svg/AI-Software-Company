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
