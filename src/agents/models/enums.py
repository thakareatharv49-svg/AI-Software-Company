from enum import StrEnum


class AgentPermission(StrEnum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    RUN_COMMANDS = "run_commands"
    RUN_TESTS = "run_tests"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"


class AgentStatus(StrEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    DISABLED = "disabled"
