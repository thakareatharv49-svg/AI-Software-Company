from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.company import review_routes
from src.company.mission_jobs import MissionJobStatus
from src.company.review_routes import publish_approved_product
from src.company.review_workflow import (
    ProductReview,
    Requirement,
    RequirementStatus,
    ReviewStatus,
    approve_review,
    prepare_review,
    update_requirement,
)
from src.config.settings import settings


class MemoryReviewStore:
    def __init__(self, review):
        self.review = review

    def get(self, mission_id):
        return self.review if self.review.mission_id == mission_id else None

    def save(self, review):
        self.review = review


@pytest.mark.asyncio
async def test_publication_requires_approved_current_artifact_and_publishes_that_revision(monkeypatch):
    mission_id = "approved-publication-acceptance"
    files = {"index.html": "<main>Expense Tracker</main>", "app.js": "console.log('approved');"}
    review = prepare_review(
        ProductReview(mission_id=mission_id),
        [Requirement(id="core-workflow", description="Core transaction workflow works")],
        qa_passed=True,
        security_passed=True,
        qa_evidence="QA suite exited with code 0",
        security_evidence="Security review approved",
        artifact_digest=review_routes._artifact_digest(files),
    )
    review = update_requirement(
        review,
        "core-workflow",
        status=RequirementStatus.PASSED,
        evidence="Transaction workflow regression tests passed",
    )
    review = approve_review(review)
    store = MemoryReviewStore(review)
    calls = []
    job = SimpleNamespace(
        id=mission_id,
        status=MissionJobStatus.COMPLETED,
        mission=SimpleNamespace(name="Expense Tracker"),
    )
    center = SimpleNamespace(_audit=lambda *args, **kwargs: None)

    monkeypatch.setattr(review_routes, "_get_job", lambda _mission_id, _center: job)
    monkeypatch.setattr(review_routes, "_workspace_files", lambda _mission_id: (None, files))
    monkeypatch.setattr(review_routes, "_review_store", lambda: store)
    monkeypatch.setattr(settings, "github_allow_writes", True)
    monkeypatch.setattr(settings, "github_token", "test-token")
    monkeypatch.setattr(settings, "github_repository_owner", "test-owner")
    monkeypatch.setattr(settings, "github_default_branch", "main")
    monkeypatch.setattr(settings, "github_api_base_url", "https://api.github.com")

    class FakeGitHubClient:
        def __init__(self, **kwargs):
            pass

    class FakeGitHubAutomation:
        def __init__(self, client):
            self.client = client

    class FakePublisher:
        def __init__(self, *, github):
            pass

        async def publish_files(self, repository, branch, product_files, message):
            calls.append((repository.owner, repository.name, branch, dict(product_files), message))
            return SimpleNamespace(success=True, message="Published successfully")

    monkeypatch.setattr(review_routes, "GitHubHttpClient", FakeGitHubClient)
    monkeypatch.setattr(review_routes, "GitHubAutomation", FakeGitHubAutomation)
    monkeypatch.setattr(review_routes, "GitHubNativeService", FakePublisher)

    # Even an approved review cannot publish files changed after approval.
    files["app.js"] = "console.log('changed after approval');"
    with pytest.raises(HTTPException) as stale:
        await publish_approved_product(mission_id, center)
    assert stale.value.status_code == 409
    assert "changed after review submission" in stale.value.detail
    assert calls == []

    # Restore the exact approved artifact and verify only that revision is sent.
    files["app.js"] = "console.log('approved');"
    published = await publish_approved_product(mission_id, center)

    assert published.status == ReviewStatus.PUBLISHED
    assert published.repository_url == "https://github.com/test-owner/expense-tracker"
    assert len(calls) == 1
    owner, repository, branch, delivered_files, message = calls[0]
    assert (owner, repository, branch) == ("test-owner", "expense-tracker", "main")
    assert delivered_files == files
    assert "approved" in message
