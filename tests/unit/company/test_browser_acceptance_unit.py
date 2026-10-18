from src.company.browser_acceptance import _safe_internal_href, _safe_interaction_label


def test_browser_route_probe_rejects_external_and_credentialed_urls():
    origin = "http://127.0.0.1:8000"

    assert _safe_internal_href("/settings", origin)
    assert _safe_internal_href("http://127.0.0.1:8000/tasks", origin)
    assert not _safe_internal_href("https://example.com/", origin)
    assert not _safe_internal_href("http://user:password@127.0.0.1:8000/", origin)


def test_browser_interaction_probe_skips_destructive_controls():
    assert _safe_interaction_label("Save")
    assert _safe_interaction_label("Open dashboard")
    assert not _safe_interaction_label("Delete project")
    assert not _safe_interaction_label("Reset")
    assert not _safe_interaction_label("Sign out")
    assert not _safe_interaction_label("")
