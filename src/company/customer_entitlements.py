"""Plan policy and fail-closed usage enforcement for customer workspaces."""
from dataclasses import dataclass

@dataclass(frozen=True)
class PlanLimits:
    monthly_runs: int
    projects: int

DEFAULT_CUSTOMER_PLAN = "demo"

PLAN_LIMITS: dict[str, PlanLimits] = {
    "demo": PlanLimits(monthly_runs=3, projects=1),
    "free": PlanLimits(monthly_runs=10, projects=3),
    "pro": PlanLimits(monthly_runs=250, projects=25),
    "team": PlanLimits(monthly_runs=1500, projects=200),
}

def resolve_limits(plan: str, *, status: str) -> PlanLimits:
    """Unknown plans and inactive subscriptions receive no quota."""
    if status != "active" or plan not in PLAN_LIMITS:
        return PlanLimits(monthly_runs=0, projects=0)
    return PLAN_LIMITS[plan]

def can_consume_run(*, runs_used: int, limit: int, status: str = "active") -> bool:
    """Check one unit without mutating state; caller must persist atomically."""
    return status == "active" and limit > 0 and runs_used < limit
