import asyncio
import json

import pytest
from fastapi import HTTPException

from src.web import routes


def test_completed_product_redirects_to_isolated_preview():
    response = asyncio.run(routes.completed_product("calculator-123"))

    assert response.status_code == 307
    assert response.headers["location"] == "/api/missions/calculator-123/review/live-preview/"
    assert response.headers["cache-control"] == "no-store"


def test_completed_product_rejects_invalid_mission_id():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.completed_product("../secrets"))

    assert exc.value.status_code == 404


def test_legacy_product_asset_redirects_through_filtered_preview():
    response = asyncio.run(
        routes.completed_product_asset("calculator-123", "assets/app.js")
    )

    assert response.status_code == 307
    assert response.headers["location"] == (
        "/api/missions/calculator-123/review/live-preview/assets/app.js"
    )


@pytest.mark.parametrize(
    "file_path",
    ["../secrets.txt", r"..\\secrets.txt", "/etc/passwd", "C:\\secrets.txt"],
)
def test_legacy_product_asset_rejects_traversal(file_path):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.completed_product_asset("calculator-123", file_path))

    assert exc.value.status_code == 404


def test_completed_products_lists_nested_browser_entrypoints(tmp_path, monkeypatch):
    mission_id = "dist-app-123"
    dist = tmp_path / mission_id / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text(
        "<html><body>Built app</body></html>", encoding="utf-8"
    )
    monkeypatch.setattr(routes, "PRODUCTS_DIR", tmp_path)
    monkeypatch.setattr(routes, "LEGACY_PRODUCTS_DIR", tmp_path / "legacy")

    response = asyncio.run(routes.completed_products())
    products = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert any(
        product.get("mission_id") == mission_id
        and product.get("url") == f"/product/{mission_id}"
        for product in products
    )
