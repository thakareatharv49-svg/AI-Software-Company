import re

from src.security.models.contracts import (
    SecurityFinding,
    SecurityScanRequest,
    SecurityScanResult,
)
from src.security.models.enums import SecuritySeverity, SecurityStatus


class SecurityScanner:
    SECRET_PATTERNS = (
        re.compile(r"""(?i)(api[_-]?key|secret|password|token)\s*=\s*['"][^'"]+['"]"""),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )

    DANGEROUS_PATTERNS = (
        re.compile(r"(?i)\beval\s*\("),
        re.compile(r"(?i)\bexec\s*\("),
        re.compile(r"(?i)\bos\.system\s*\("),
        re.compile(r"(?i)\bsubprocess\.(?:run|Popen|call)\s*\("),
    )

    def scan(self, request: SecurityScanRequest) -> SecurityScanResult:
        findings: list[SecurityFinding] = []

        for path, content in request.files.items():
            for line_number, line in enumerate(content.splitlines(), start=1):
                for pattern in self.SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            SecurityFinding(
                                rule="secret-detection",
                                severity=SecuritySeverity.CRITICAL,
                                message="Potential hard-coded secret detected",
                                path=path,
                                line=line_number,
                            )
                        )
                        break

                for pattern in self.DANGEROUS_PATTERNS:
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

        status = (
            SecurityStatus.FAILED
            if findings
            else SecurityStatus.PASSED
        )

        return SecurityScanResult(
            status=status,
            findings=findings,
        )
