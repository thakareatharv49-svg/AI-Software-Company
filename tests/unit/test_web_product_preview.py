import asyncio

from src.web import routes


def test_completed_product_sets_base_url_for_relative_browser_assets(tmp_path, monkeypatch):
    mission_id = "calculator-123"
    product_dir = tmp_path / mission_id
    product_dir.mkdir()
    (product_dir / "index.html").write_text(
        '<!doctype html><html><head><title>Calculator</title>'
        '<link rel="stylesheet" href="style.css"></head>'
        '<body><script src="app.js"></script></body></html>',
        encoding="utf-8",
    )
    (product_dir / "style.css").write_text("body { color: white; }", encoding="utf-8")
    (product_dir / "app.js").write_text("document.body.dataset.ready = 'yes';", encoding="utf-8")
    monkeypatch.setattr(routes, "PRODUCTS_DIR", tmp_path)
    monkeypatch.setattr(routes, "LEGACY_PRODUCTS_DIR", tmp_path / "legacy")

    response = asyncio.run(routes.completed_product(mission_id))

    html = response.body.decode("utf-8")
    assert response.status_code == 200
    assert '<base href="/product/calculator-123/">' in html
    assert 'href="style.css"' in html
    assert 'src="app.js"' in html


def test_completed_product_uses_legacy_preview_when_current_folder_has_no_index(tmp_path, monkeypatch):
    mission_id = "calculator-legacy"
    current_dir = tmp_path / "current" / mission_id
    legacy_dir = tmp_path / "legacy" / mission_id
    current_dir.mkdir(parents=True)
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "index.html").write_text(
        '<!doctype html><html><head><title>Legacy calculator</title></head></html>',
        encoding="utf-8",
    )
    monkeypatch.setattr(routes, "PRODUCTS_DIR", tmp_path / "current")
    monkeypatch.setattr(routes, "LEGACY_PRODUCTS_DIR", tmp_path / "legacy")

    response = asyncio.run(routes.completed_product(mission_id))

    assert response.status_code == 200
    assert "Legacy calculator" in response.body.decode("utf-8")
    assert '<base href="/product/calculator-legacy/">' in response.body.decode("utf-8")
