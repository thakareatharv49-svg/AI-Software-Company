from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from src.company import review_routes
from src.company.mission_jobs import MissionJobStatus


def _request(host: bytes = b"testserver") -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [(b"host", host)],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1234),
        }
    )


def _completed_job():
    return SimpleNamespace(
        status=MissionJobStatus.COMPLETED,
        mission=SimpleNamespace(name="Demo product"),
    )


def test_live_preview_returns_html_with_restrictive_sandbox_headers(monkeypatch):
    monkeypatch.setattr(review_routes, "_get_job", lambda mission_id, center: _completed_job())
    monkeypatch.setattr(
        review_routes,
        "_workspace_files",
        lambda mission_id: (
            None,
            {
                "index.html": '<!doctype html><link rel="stylesheet" href="style.css"><h1>Demo</h1>',
                "style.css": "h1 { color: navy; }",
            },
        ),
    )

    response = review_routes.live_product_preview("mission-123", _request(), None)

    assert response.status_code == 200
    assert "<h1>Demo</h1>" in response.body.decode()
    policy = response.headers["content-security-policy"]
    assert "sandbox allow-scripts" in policy
    assert "connect-src 'none'" in policy
    assert "form-action 'none'" in policy
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_live_preview_requires_completed_job_and_root_index(monkeypatch):
    monkeypatch.setattr(
        review_routes,
        "_get_job",
        lambda mission_id, center: SimpleNamespace(
            status=MissionJobStatus.QUEUED,
            mission=SimpleNamespace(name="Demo product"),
        ),
    )
    with pytest.raises(HTTPException) as queued:
        review_routes.live_product_preview("mission-123", _request(), None)
    assert queued.value.status_code == 409

    monkeypatch.setattr(review_routes, "_get_job", lambda mission_id, center: _completed_job())
    monkeypatch.setattr(review_routes, "_workspace_files", lambda mission_id: (None, {"main.py": "print('hi')"}))
    with pytest.raises(HTTPException) as missing:
        review_routes.live_product_preview("mission-123", _request(), None)
    assert missing.value.status_code == 422


def test_live_preview_asset_serves_only_workspace_text_and_rejects_traversal(monkeypatch):
    monkeypatch.setattr(review_routes, "_get_job", lambda mission_id, center: _completed_job())
    monkeypatch.setattr(
        review_routes,
        "_workspace_files",
        lambda mission_id: (None, {"assets/app.js": "console.log('safe')"}),
    )

    response = review_routes.live_product_preview_asset(
        "mission-123", "assets/app.js", _request(), None
    )
    assert response.body.decode() == "console.log('safe')"
    assert response.media_type == "text/javascript"

    with pytest.raises(HTTPException) as traversal:
        review_routes.live_product_preview_asset(
            "mission-123", "../secrets.txt", _request(), None
        )
    assert traversal.value.status_code == 404

    with pytest.raises(HTTPException) as missing:
        review_routes.live_product_preview_asset(
            "mission-123", "assets/missing.js", _request(), None
        )
    assert missing.value.status_code == 404


def test_live_preview_rejects_untrusted_host_header(monkeypatch):
    monkeypatch.setattr(review_routes, "_get_job", lambda mission_id, center: _completed_job())
    monkeypatch.setattr(review_routes, "_workspace_files", lambda mission_id: (None, {"index.html": "<h1>ok</h1>"}))

    with pytest.raises(HTTPException) as invalid:
        review_routes.live_product_preview(
            "mission-123", _request(b"example.com; script-src *"), None
        )
    assert invalid.value.status_code == 400
