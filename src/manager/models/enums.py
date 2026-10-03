from enum import StrEnum


class ManagerStatus(StrEnum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class ManagerDecisionType(StrEnum):
    WAIT = "wait"
    START_TASK = "start_task"
    COMPLETE_MISSION = "complete_mission"
    BLOCK = "block"
