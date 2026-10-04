from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.security.models.contracts import SecurityAction, SecurityPolicy
from src.security.routes.routes import router
from src.security.service.service import PermissionService


def test_github_writes_are_denied_by_default() -> None:
    service = PermissionService(SecurityPolicy(allow_github_writes=False))
    decision = service.authorize(SecurityAction.GITHUB_WRITE)

    assert decision.allowed is False
    assert "explicit" in decision.reason


def test_shell_execution_is_denied_by_default() -> None:
    service = PermissionService(SecurityPolicy(allow_shell_execution=False))
    decision = service.authorize(SecurityAction.SHELL_EXECUTE)

    assert decision.allowed is False


def test_explicit_github_permission_is_allowed() -> None:
    service = PermissionService(SecurityPolicy(allow_github_writes=True))
    decision = service.authorize(SecurityAction.GITHUB_WRITE)

    assert decision.allowed is True


def test_security_route() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/security/permissions")

    assert response.status_code == 200
    actions = {item["action"] for item in response.json()}
    assert "github.write" in actions
    assert "shell.execute" in actions


def test_security_headers() -> None:
    from src.main import app

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
