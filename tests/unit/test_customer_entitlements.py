from src.company.customer_entitlements import DEFAULT_CUSTOMER_PLAN, PLAN_LIMITS, can_consume_run, resolve_limits
from src.db.base import Base
from src.db.models.entitlement import WorkspaceEntitlementModel, WorkspaceUsageModel


def test_plan_limits_are_server_defined_and_increasing() -> None:
    assert DEFAULT_CUSTOMER_PLAN == "demo"
    assert PLAN_LIMITS["demo"].monthly_runs == 3
    assert PLAN_LIMITS["demo"].projects == 1
    assert PLAN_LIMITS[DEFAULT_CUSTOMER_PLAN].monthly_runs == 3
    assert PLAN_LIMITS["pro"].monthly_runs > PLAN_LIMITS["free"].monthly_runs
    assert PLAN_LIMITS["team"].projects > PLAN_LIMITS["pro"].projects


def test_unknown_plan_and_inactive_subscription_fail_closed() -> None:
    assert resolve_limits("unrecognized", status="active").monthly_runs == 0
    assert resolve_limits("pro", status="cancelled").projects == 0
    assert not can_consume_run(runs_used=0, limit=100, status="past_due")


def test_quota_rejects_when_limit_reached() -> None:
    assert can_consume_run(runs_used=2, limit=3)
    assert not can_consume_run(runs_used=3, limit=3)
    assert not can_consume_run(runs_used=0, limit=0)


def test_usage_models_are_registered_with_database_metadata() -> None:
    assert WorkspaceEntitlementModel.__tablename__ in Base.metadata.tables
    assert WorkspaceUsageModel.__tablename__ in Base.metadata.tables
    constraints = WorkspaceUsageModel.__table__.constraints
    assert any(getattr(item, "name", None) == "uq_workspace_usage_period" for item in constraints)
