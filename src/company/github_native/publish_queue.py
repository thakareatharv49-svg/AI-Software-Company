from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class GitHubPublishQueue:
    """Small persistent queue for GitHub publishes deferred by rate limits."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (
            Path(__file__).resolve().parents[2]
            / "generated-products"
            / ".github-publish-queue"
        )
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(owner: str, name: str, branch: str) -> str:
        raw = f"{owner}/{name}:{branch}".encode()
        return hashlib.sha256(raw).hexdigest()[:24]

    def enqueue(
        self,
        *,
        owner: str,
        name: str,
        branch: str,
        files: dict[str, str],
        message: str,
        delay_seconds: int = 60,
    ) -> None:
        key = self._key(owner, name, branch)
        path = self.root / f"{key}.json"
        attempts = 0
        if path.is_file():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
                attempts = int(previous.get("attempts", 0))
            except (OSError, ValueError, TypeError):
                attempts = 0
        attempts += 1
        backoff = max(delay_seconds, min(3600, 60 * (2 ** min(attempts - 1, 5))))
        payload: dict[str, Any] = {
            "owner": owner,
            "name": name,
            "branch": branch,
            "files": files,
            "message": message,
            "attempts": attempts,
            "not_before": time.time() + backoff,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    def due(self) -> list[dict[str, Any]]:
        now = time.time()
        entries: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if float(payload.get("not_before", 0)) <= now:
                payload["_path"] = str(path)
                entries.append(payload)
        return entries

    @staticmethod
    def remove(entry: dict[str, Any]) -> None:
        path = entry.get("_path")
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass
