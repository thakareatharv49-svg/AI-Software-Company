import pytest
from fastapi import HTTPException

from src.company import review_routes


def test_workspace_preview_filters_secrets_and_generated_dependencies(tmp_path, monkeypatch):
    products = tmp_path / "generated-products"
    workspace = products / "mission-123"
    workspace.mkdir(parents=True)
    (workspace / "main.py").write_text("print('safe')", encoding="utf-8")
    (workspace / ".env.example").write_text("API_KEY=replace-me", encoding="utf-8")
    (workspace / ".env").write_text("API_KEY=real-secret", encoding="utf-8")
    (workspace / "private.pem").write_text("private-key", encoding="utf-8")
    dependencies = workspace / "node_modules"
    dependencies.mkdir()
    (dependencies / "package.js").write_text("ignored", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside workspace", encoding="utf-8")
    (workspace / "outside-link.txt").symlink_to(outside)

    monkeypatch.setattr(review_routes, "PRODUCTS_ROOT", products)

    root, files = review_routes._workspace_files("mission-123")

    assert root == workspace
    assert files == {
        ".env.example": "API_KEY=replace-me",
        "main.py": "print('safe')",
    }


def test_workspace_preview_rejects_path_traversal_and_missing_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(review_routes, "PRODUCTS_ROOT", tmp_path / "generated-products")

    with pytest.raises(HTTPException) as traversal:
        review_routes._workspace_files("../outside")
    assert traversal.value.status_code == 404

    with pytest.raises(HTTPException) as missing:
        review_routes._workspace_files("missing-mission")
    assert missing.value.status_code == 404
