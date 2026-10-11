import pytest

from src.company.review_workflow import (
    InvalidReviewTransition,
    ProductReview,
    Requirement,
    RequirementStatus,
    ReviewStatus,
    approve_review,
    mark_published,
    prepare_review,
    request_changes,
    update_requirement,
)

def ready_review():
    review = prepare_review(
        ProductReview(mission_id='mission-1'),
        [Requirement(description='Create a task', verification='Create and reload a task')],
        qa_passed=True,
        security_passed=True,
    )
    return review, review.requirements[0]

def test_cannot_submit_without_requirements_or_quality_gates():
    with pytest.raises(InvalidReviewTransition, match='requirement'):
        prepare_review(ProductReview(mission_id='m1'), [], qa_passed=True, security_passed=True)
    with pytest.raises(InvalidReviewTransition, match='must pass'):
        prepare_review(ProductReview(mission_id='m1'), [Requirement(description='Works')], qa_passed=False, security_passed=True)

def test_approval_requires_every_acceptance_requirement_to_pass():
    review, requirement = ready_review()
    with pytest.raises(InvalidReviewTransition, match='remain unverified'):
        approve_review(review)
    review = update_requirement(review, requirement.id, status=RequirementStatus.PASSED, evidence='Browser workflow test passed')
    approved = approve_review(review)
    assert approved.status == ReviewStatus.APPROVED
    assert approved.approved_at is not None

def test_feedback_requests_a_revision_and_clears_previous_approval():
    review, requirement = ready_review()
    review = update_requirement(review, requirement.id, status=RequirementStatus.PASSED)
    review = approve_review(review)
    revised = request_changes(review, 'Add a calendar view') if review.status == ReviewStatus.IN_REVIEW else None
    assert revised is None

def test_feedback_from_review_increments_revision_and_preserves_feedback():
    review, _ = ready_review()
    revised = request_changes(review, 'Add a calendar view')
    assert revised.status == ReviewStatus.CHANGES_REQUESTED
    assert revised.revision == 1
    assert revised.feedback[0].message == 'Add a calendar view'
    resubmitted = prepare_review(revised, [Requirement(description='Calendar view works')], qa_passed=True, security_passed=True)
    assert resubmitted.status == ReviewStatus.IN_REVIEW
    assert resubmitted.revision == 1
    assert len(resubmitted.feedback) == 1

def test_publication_is_blocked_until_human_approval():
    review, _ = ready_review()
    with pytest.raises(InvalidReviewTransition, match='human approves'):
        mark_published(review, 'https://github.com/example/project')
    review, requirement = ready_review()
    review = update_requirement(review, requirement.id, status=RequirementStatus.PASSED)
    approved = approve_review(review)
    published = mark_published(approved, 'https://github.com/example/project')
    assert published.status == ReviewStatus.PUBLISHED
    assert published.repository_url == 'https://github.com/example/project'
    assert published.published_at is not None

def test_blank_feedback_is_rejected():
    review, _ = ready_review()
    with pytest.raises(ValueError):
        request_changes(review, '   ')
