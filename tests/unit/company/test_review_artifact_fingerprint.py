import pytest
from fastapi import HTTPException

from src.company.review_routes import _artifact_digest, _require_current_review_artifact
from src.company.review_workflow import ProductReview, Requirement, prepare_review, request_changes


def ready_review(files):
    return prepare_review(
        ProductReview(mission_id="fingerprint-test"),
        [Requirement(description="The product workflow works")],
        qa_passed=True,
        security_passed=True,
        qa_evidence="CI QA passed",
        security_evidence="Server security check passed",
        artifact_digest=_artifact_digest(files),
    )


def test_artifact_digest_is_stable_and_order_independent():
    first = {"index.html": "<main>Ready</main>", "app.js": "console.log('ok')"}
    second = {"app.js": "console.log('ok')", "index.html": "<main>Ready</main>"}

    assert _artifact_digest(first) == _artifact_digest(second)


def test_current_artifact_can_be_approved_for_review():
    files = {"index.html": "<main>Ready</main>"}
    review = ready_review(files)

    _require_current_review_artifact(review, files)


def test_changed_artifact_is_blocked_from_review_approval():
    review = ready_review({"index.html": "<main>Ready</main>"})

    with pytest.raises(HTTPException) as exc:
        _require_current_review_artifact(
            review, {"index.html": "<main>Changed after QA</main>"}
        )

    assert exc.value.status_code == 409
    assert "changed after review submission" in exc.value.detail


def test_review_without_fingerprint_must_be_resubmitted():
    review = ProductReview(mission_id="legacy-review", status="in_review")

    with pytest.raises(HTTPException) as exc:
        _require_current_review_artifact(review, {"index.html": "<main>Ready</main>"})

    assert exc.value.status_code == 409
    assert "no artifact fingerprint" in exc.value.detail


def test_requesting_changes_invalidates_the_old_artifact_fingerprint():
    review = ready_review({"index.html": "<main>Ready</main>"})

    revised = request_changes(review, "Fix the settings screen")

    assert revised.artifact_digest is None
