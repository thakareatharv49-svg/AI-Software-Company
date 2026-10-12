from __future__ import annotations

import re
from collections.abc import Mapping

# Findings intentionally omit matched values to prevent accidental secret leakage.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("stripe-secret-key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("bearer-token", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{20,}={0,2}")),
    (
        "credential-assignment",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|client[_-]?secret|password|passwd|secret|token|auth[_-]?token|refresh[_-]?token|access[_-]?token|private[_-]?key|database[_-]?url|connection[_-]?string|authorization)\b"""
            r"""\s*[:=]\s*['"]?([A-Za-z0-9_./:@+=-]{12,})"""
        ),
    ),
)
_PLACEHOLDER_PREFIXES = (
    "your_", "your-", "replace_", "replace-", "changeme", "change_me",
    "example", "dummy", "placeholder", "insert_", "todo_", "\${",
)


def scan_generated_secrets(files: Mapping[str, str]) -> list[str]:
    """Return value-free findings for likely hard-coded credentials."""
    findings: list[str] = []
    for path, content in files.items():
        if not isinstance(path, str) or not isinstance(content, str):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule, pattern in _PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                candidate = match.group(1) if rule == "credential-assignment" else match.group(0)
                if candidate.casefold().startswith(_PLACEHOLDER_PREFIXES):
                    continue
                findings.append(
                    f"Generated artifact '{path}' line {line_number} may contain a secret ({rule}); "
                    "remove it and use a runtime secret store."
                )
                break
    return findings
