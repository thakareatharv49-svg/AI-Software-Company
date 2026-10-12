from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.company import review_routes
from src.company.mission_jobs import MissionJobStatus
from src.company.review_routes import (
    RequirementUpdateRequest,
    SubmitReviewRequest,
    approve_product,
    submit_product_for_review,
    verify_product_requirement,
)
from src.company.review_workflow import Requirement, RequirementStatus, request_changes


class MemoryReviewStore:
    def __init__(self):
        self.items = {}

    def get(self, mission_id):
        return self.items.get(mission_id)

    def save(self, review):
        self.items[review.mission_id] = review


def test_review_revision_requires_reapproval_of_the_exact_new_artifact(monkeypatch):
    mission_id = "review-revision-acceptance"
    center = object()
    files = {"index.html": "<main>Transactions</main>", "app.js": "const ready = true;"}
    store = MemoryReviewStore()
    job = SimpleNamespace(
        status=MissionJobStatus.COMPLETED,
        plan=SimpleNamespace(
            qa_status="passed",
            qa_evidence="QA command exited 0 with tests passing",
            security_status="approved",
            security_evidence="Security checks passed for this revision",
        ),
    )
    monkeypatch.setattr(review_routes, "_get_job", lambda _mission_id, _center: job)
    monkeypatch.setattr(review_routes, "_workspace_files", lambda _mission_id: (None, files))
    monkeypatch.setattr(review_routes, "_review_store", lambda: store)

    requirements = [
        Requirement(
            id="transaction-workflow",
            description="Users can manage transactions",
            verification="Create, edit, delete and search a transaction",
        )
    ]
    submitted = submit_product_for_review(
        mission_id,
        SubmitReviewRequest(requirements=requirements),
        center,
    )
    assert submitted.status.value == "in_review"
    assert submitted.artifact_digest

    verified = verify_product_requirement(
        mission_id,
        "transaction-workflow",
        RequirementUpdateRequest(
            status=RequirementStatus.PASSED,
            evidence="Create, edit, delete and search verified by the acceptance suite",
        ),
        center,
    )
    assert verified.requirements[0].status == RequirementStatus.PASSED

    # A post-review code change invalidates the original approval request.
    files["app.js"] = "const ready = false;"
    with pytest.raises(HTTPException) as stale:
        approve_product(mission_id, center)
    assert stale.value.status_code == 409
    assert "changed after review submission" in stale.value.detail

    # Simulate a requested revision. Resubmission binds review to the new files
    # and resets acceptance requirements so they must be verified again.
    store.save(request_changes(store.get(mission_id), "Fix the transaction workflow"))
    resubmitted = submit_product_for_review(
        mission_id,
        SubmitReviewRequest(requirements=requirements),
        center,
    )
    assert resubmitted.artifact_digest != submitted.artifact_digest
    assert resubmitted.requirements[0].status == RequirementStatus.PENDING

    verify_product_requirement(
        mission_id,
        "transaction-workflow",
        RequirementUpdateRequest(
            status=RequirementStatus.PASSED,
            evidence="Re-tested the revised transaction workflow",
        ),
        center,
    )
    approved = approve_product(mission_id, center)
    assert approved.status.value == "approved"
    assert approved.artifact_digest == resubmitted.artifact_digest
