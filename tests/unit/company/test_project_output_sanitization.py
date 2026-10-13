from datetime import UTC, datetime

from src.company.persistence import _safe_output_manifest
from src.company.project_outputs import ProjectOutputManifest


def test_project_output_metadata_is_redacted_and_bounded() -> None:
    manifest = ProjectOutputManifest(
        id="output-1",
        mission_id="mission-1",
        project_id="project-1",
        name="Product",
        status="ready",
        repository="https://user:supersecret@example.com/repo",
        product_url="https://example.com/?token=verylongsecretvalue123456",
        github_message="published with password=hunter2 and " + ("x" * 3000),
        memory_id="memory-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    safe = _safe_output_manifest(manifest)

    assert "supersecret" not in (safe.repository or "")
    assert "verylongsecretvalue123456" not in (safe.product_url or "")
    assert "hunter2" not in (safe.github_message or "")
    assert len(safe.github_message or "") == 2000
    assert safe.status == "ready"
    assert safe.created_at == manifest.created_at
    assert safe.updated_at == manifest.updated_at


def test_project_output_manifest_sanitization_preserves_optional_values() -> None:
    manifest = ProjectOutputManifest(
        id="output-2",
        mission_id="mission-2",
        project_id="project-2",
        name="Ordinary product",
        status="pending_review",
    )

    safe = _safe_output_manifest(manifest)

    assert safe.repository is None
    assert safe.product_url is None
    assert safe.github_message is None
    assert safe.status == "pending_review"
