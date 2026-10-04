from enum import StrEnum


class MemoryType(StrEnum):
    EVENT = "event"
    COMPANY = "company"
    PROJECT = "project"
    TECHNICAL = "technical"
    DECISION = "decision"
    FAILURE = "failure"
    AGENT_PERFORMANCE = "agent_performance"
