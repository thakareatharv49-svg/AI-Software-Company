from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.company.control_center.routes import get_control_center
from src.main import app
from src.security.customer_authorization import require_customer_workspace
from src.web import customer_routes


def _job(mission_id: str, workspace_id: str, status: str = "completed"):
    return SimpleNamespace(id=mission_id, workspace_id=workspace_id, status=SimpleNamespace(value=status))


class _Center:
    def __init__(self):
        self.jobs = {
            "owned": _job("owned", "workspace-a"),
            "foreign": _job("foreign", "workspace-b"),
        }

    def mission_job(self, mission_id: str):
        return self.jobs.get(mission_id)


def test_customer_workspace_page_is_available_without_owner_console():
    response = TestClient(app).get("/customer")
    assert response.status_code == 200
    assert "YOUR WORKSPACE" in response.text
    assert "customer.js" in response.text


def test_customer_product_preview_is_workspace_scoped(tmp_path, monkeypatch):
    product = tmp_path / "owned"
    product.mkdir()
    (product / "index.html").write_text(
        "<!doctype html><html><head><title>Preview</title></head><body>Hello</body></html>",
        encoding="utf-8",
    )
    monkeypatch.setattr(customer_routes, "PRODUCTS_DIR", tmp_path)
    monkeypatch.setattr(customer_routes, "LEGACY_PRODUCTS_DIR", tmp_path / "legacy")
    app.dependency_overrides[require_customer_workspace] = lambda: (None, SimpleNamespace(id="workspace-a"))
    app.dependency_overrides[get_control_center] = lambda: _Center()
    try:
        client = TestClient(app)
        response = client.get("/customer/products/owned")
        assert response.status_code == 200
        assert '<base href="/customer/products/owned/">' in response.text
        assert client.get("/customer/products/foreign").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_customer_product_preview_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(customer_routes, "PRODUCTS_DIR", tmp_path)
    monkeypatch.setattr(customer_routes, "LEGACY_PRODUCTS_DIR", tmp_path / "legacy")
    app.dependency_overrides[require_customer_workspace] = lambda: (None, SimpleNamespace(id="workspace-a"))
    app.dependency_overrides[get_control_center] = lambda: _Center()
    try:
        response = TestClient(app).get("/customer/products/owned/../../secret.txt")
        assert response.status_code in (404, 422)
    finally:
        app.dependency_overrides.clear()
