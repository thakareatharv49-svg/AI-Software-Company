from enum import StrEnum


class QATestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class DebugStatus(StrEnum):
    NOT_NEEDED = "not_needed"
    RETRYING = "retrying"
    RESOLVED = "resolved"
    BLOCKED = "blocked"
