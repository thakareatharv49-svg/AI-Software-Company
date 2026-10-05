from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class DataClass(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PII = "pii"
    SECRET = "secret"


@dataclass(frozen=True)
class GovernanceFinding:
    category: str
    data_class: DataClass
    detail: str


@dataclass(frozen=True)
class GovernanceReport:
    findings: tuple[GovernanceFinding, ...]

    @property
    def has_secret(self) -> bool:
        return any(item.data_class == DataClass.SECRET for item in self.findings)

    @property
    def has_pii(self) -> bool:
        return any(item.data_class == DataClass.PII for item in self.findings)


class DataGovernance:
    """M39 data classification, secret/PII detection and repository governance."""

    _EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
    _SECRET = re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^\s'\"]+"
    )

    def inspect(self, content: str) -> GovernanceReport:
        findings: list[GovernanceFinding] = []
        if self._SECRET.search(content):
            findings.append(
                GovernanceFinding(
                    "secret",
                    DataClass.SECRET,
                    "Potential credential or secret detected.",
                )
            )
        if self._EMAIL.search(content):
            findings.append(
                GovernanceFinding(
                    "pii",
                    DataClass.PII,
                    "Potential email address detected.",
                )
            )
        if not findings:
            findings.append(
                GovernanceFinding(
                    "classification",
                    DataClass.PUBLIC,
                    "No PII or secret pattern detected.",
                )
            )
        return GovernanceReport(tuple(findings))

    def validate_repository(self, files: dict[str, str]) -> GovernanceReport:
        findings: list[GovernanceFinding] = []
        for path, content in files.items():
            report = self.inspect(content)
            findings.extend(
                GovernanceFinding(
                    finding.category,
                    finding.data_class,
                    f"{path}: {finding.detail}",
                )
                for finding in report.findings
                if finding.data_class in (DataClass.PII, DataClass.SECRET)
            )
        return GovernanceReport(tuple(findings))

    @staticmethod
    def retention_allowed(data_class: DataClass, retention_days: int) -> bool:
        if retention_days < 0:
            raise ValueError("retention_days cannot be negative")
        if data_class == DataClass.SECRET:
            return retention_days == 0
        return True
