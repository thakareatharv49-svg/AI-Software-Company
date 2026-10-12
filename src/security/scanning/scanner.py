"""Heuristic security scanner for generated files before review or publication.

This scanner is a defense-in-depth signal, not a replacement for secret-management
controls, OS sandboxing, or a dedicated secret scanner.
"""
import re
from pathlib import PurePosixPath

from src.security.models.contracts import (
    SecurityFinding,
    SecurityScanRequest,
    SecurityScanResult,
)
from src.security.models.enums import SecuritySeverity, SecurityStatus


_PLACEHOLDER = r"(?:changeme|change_me|example|placeholder|your[_ -].*|<[^>]+>|\$\{[^}]+\})"
_QUOTED_VALUE = r"""['"]([^'"]{8,})['"]"""
_ASSIGNMENT_SECRET = re.compile(
    rf"""(?i)\b(?:api[_-]?key|client[_-]?secret|secret[_-]?key|password|passwd|access[_-]?token|auth[_-]?token)\s*[:=]\s*{_QUOTED_VALUE}"""
)
_ENV_SECRET = re.compile(
    rf"""(?i)\b(?:AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|GH_TOKEN|OPENAI_API_KEY|SUPABASE_SERVICE_ROLE_KEY)\s*=\s*{_QUOTED_VALUE}"""
)
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
)
_AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GITHUB_TOKEN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{20,}")
_DATABASE_CREDENTIAL = re.compile(
    r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@"
)
_DANGEROUS_PATTERNS = (
    re.compile(r"(?i)\beval\s*\("),
    re.compile(r"(?i)\bexec\s*\("),
    re.compile(r"(?i)\bos\.system\s*\("),
    re.compile(r"(?i)\bsubprocess\.(?:run|Popen|call|check_call|check_output)\s*\("),
    re.compile(r"(?i)\bshell\s*=\s*True\b"),
)
_SECRET_PATTERNS = (
    ("secret-assignment", _ASSIGNMENT_SECRET),
    ("environment-secret", _ENV_SECRET),
    ("private-key", _PRIVATE_KEY),
    ("aws-access-key", _AWS_ACCESS_KEY),
    ("github-token", _GITHUB_TOKEN),
    ("bearer-token", _BEARER_TOKEN),
    ("database-credential", _DATABASE_CREDENTIAL),
)
_PLACEHOLDER_RE = re.compile(rf"(?i)^{_PLACEHOLDER}$")


class SecurityScanner:
    """Detect common embedded credentials and risky code patterns."""

    def scan(self, request: SecurityScanRequest) -> SecurityScanResult:
        findings: list[SecurityFinding] = []

        for raw_path, content in request.files.items():
            path = str(PurePosixPath(raw_path.replace("\\", "/")))
            for line_number, line in enumerate(content.splitlines(), start=1):
                for rule, pattern in _SECRET_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        candidate = match.group(1) if match.lastindex else match.group(0)
                        if rule in {"secret-assignment", "environment-secret"} and _PLACEHOLDER_RE.match(candidate):
                            continue
                        findings.append(
                            SecurityFinding(
                                rule=rule,
                                severity=SecuritySeverity.CRITICAL,
                                message="Potential hard-coded credential detected; value redacted",
                                path=path,
                                line=line_number,
                            )
                        )
                        break

                for pattern in _DANGEROUS_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            SecurityFinding(
                                rule="dangerous-command",
                                severity=SecuritySeverity.HIGH,
                                message="Potentially dangerous command execution detected",
                                path=path,
                                line=line_number,
                            )
                        )
                        break

        status = SecurityStatus.FAILED if findings else SecurityStatus.PASSED
        return SecurityScanResult(status=status, findings=findings)
