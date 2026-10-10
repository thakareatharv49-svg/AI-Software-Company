from fastapi.testclient import TestClient

from src.main import app


def test_private_company_routes_reject_anonymous_requests() -> None:
    client = TestClient(app)
    paths = (
        "/app",
        "/api/company/state",
        "/api/company/readiness",
        "/api/missions",
        "/api/mission-jobs",
        "/api/factory/status",
        "/api/products",
        "/security/permissions",
    )

    for path in paths:
        response = client.get(path)
        assert response.status_code == 401, (path, response.status_code, response.text)


def test_private_company_mutations_reject_anonymous_requests() -> None:
    client = TestClient(app)
    paths = (
        "/api/company/stop",
        "/api/company/block?reason=test",
        "/api/factory/run-queue",
        "/api/missions/unknown/retry",
        "/api/missions/unknown/execute-all",
    )

    for path in paths:
        response = client.post(path)
        assert response.status_code == 401, (path, response.status_code, response.text)


def test_authentication_endpoints_remain_reachable_without_a_session() -> None:
    client = TestClient(app)
    response = client.get("/auth/me")
    assert response.status_code == 401
    # OAuth start remains public; missing provider configuration is a controlled
    # 503 rather than being blocked by the private-company authorization layer.
    response = client.get("/auth/google/start", follow_redirects=False)
    assert response.status_code in (302, 503)
    assert response.status_code != 401


def test_owner_console_shell_loads_before_authentication() -> None:
    client = TestClient(app)
    response = client.get("/owner")

    assert response.status_code == 200
    assert "Owner Console" in response.text
    assert "/auth/google/start" in response.text
    assert "/auth/github/start" in response.text

