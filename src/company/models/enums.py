from enum import StrEnum


class CompanyStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    STOPPED = "stopped"


class CompanyDecision(StrEnum):
    CONTINUE = "continue"
    COMPLETE_PROJECT = "complete_project"
    BLOCK = "block"
    STOP = "stop"
