from __future__ import annotations

import re
from typing import Any

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----.*?"
            r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/-]{12,}={0,2}"),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"\b(?:gh[pousr]_|xox[baprs]-|sk-(?:proj-)?|AIza|AKIA)[A-Za-z0-9_-]{12,}\b"),
        "[REDACTED_TOKEN]",
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "[REDACTED_JWT]",
    ),
    (
        re.compile(
            r"""(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|database[_-]?url|connection[_-]?string)\b"""
            r"""(\s*[:=]\s*['"]?)[^\s,'";]+"""
        ),
        r"\1\2[REDACTED]",
    ),
    (
        re.compile(r"(://[^:/@\s]+:)[^@\s]+(@)"),
        r"\1[REDACTED]\2",
    ),
)


def redact_sensitive_text(value: str) -> str:
    """Redact common credential forms before errors or tool output are exposed."""
    redacted = value
    for pattern, replacement in _PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_sensitive_value(value: Any) -> Any:
    """Redact string values recursively without changing the shape of common data."""
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if re.search(
                    r"(?i)(password|passwd|secret|token|api[_-]?key|authorization|private[_-]?key|database[_-]?url|connection[_-]?string|credential)",
                    str(key),
                )
                else redact_sensitive_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_value(item) for item in value)
    return value
