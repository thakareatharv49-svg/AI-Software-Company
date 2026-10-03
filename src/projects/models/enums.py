from enum import StrEnum


class ProjectStatus(StrEnum):
    IDEA = "idea"
    RESEARCH = "research"
    VALIDATION = "validation"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEBUGGING = "debugging"
    SECURITY = "security"
    REVIEW = "review"
    RELEASE = "release"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"
