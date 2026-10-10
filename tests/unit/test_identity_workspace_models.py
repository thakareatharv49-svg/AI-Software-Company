from src.db.base import Base
from src.db.models import (
    AuthSessionModel,
    OAuthIdentityModel,
    UserModel,
    WorkspaceMembershipModel,
    WorkspaceModel,
)


def test_identity_and_workspace_tables_are_registered() -> None:
    expected = {
        "app_users",
        "auth_sessions",
        "oauth_identities",
        "workspaces",
        "workspace_memberships",
    }
    assert expected.issubset(Base.metadata.tables)


def test_oauth_identity_has_unique_provider_subject_constraint() -> None:
    constraints = OAuthIdentityModel.__table__.constraints
    assert any(
        getattr(constraint, "name", None) == "uq_oauth_provider_subject"
        for constraint in constraints
    )


def test_workspace_kind_and_membership_role_are_constrained() -> None:
    workspace_constraints = WorkspaceModel.__table__.constraints
    membership_constraints = WorkspaceMembershipModel.__table__.constraints
    assert any(
        getattr(constraint, "name", None) == "ck_workspaces_kind"
        for constraint in workspace_constraints
    )
    assert any(
        getattr(constraint, "name", None) == "ck_workspace_membership_role"
        for constraint in membership_constraints
    )


def test_sessions_store_a_token_hash_not_a_raw_token() -> None:
    columns = AuthSessionModel.__table__.columns
    assert "token_hash" in columns
    assert "token" not in columns
    assert UserModel.__tablename__ == "app_users"
