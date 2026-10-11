import pytest

from src.company.review_workflow import (
    InvalidReviewTransition, ProductReview, Requirement, RequirementStatus,
    ReviewStatus, approve_review, mark_published, prepare_review,
    request_changes, update_requirement,
)

def ready_review():
    review = prepare_review(
        ProductReview(mission_id='mission-1'),
        [Requirement(description='Create a task', verification='Create and reload a task')],
        qa_passed=True, security_passed=True,
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

def test_feedback_requests_revision_and_resubmission_preserves_history():
    review, _ = ready_review()
    revised = request_changes(review, 'Add a calendar view')
    assert revised.status == ReviewStatus.CHANGES_REQUESTED
    assert revised.revision == 1
    assert revised.feedback[0].message == 'Add a calendar view'
    original_requirement_id = review.requirements[0].id
    resubmitted = prepare_review(revised, [Requirement(description='Create a task'), Requirement(description='Calendar view works')], qa_passed=True, security_passed=True)
    assert resubmitted.status == ReviewStatus.IN_REVIEW
    assert resubmitted.revision == 1
    assert len(resubmitted.feedback) == 1
    assert len(resubmitted.requirements) == 2
    assert resubmitted.requirements[0].id == original_requirement_id
    assert all(item.status == RequirementStatus.PENDING for item in resubmitted.requirements)

def test_approved_review_cannot_be_reopened_as_a_change_request():
    review, requirement = ready_review()
    review = update_requirement(review, requirement.id, status=RequirementStatus.PASSED)
    approved = approve_review(review)
    with pytest.raises(InvalidReviewTransition, match='Cannot request changes'):
        request_changes(approved, 'Add a calendar view')

def test_publication_is_blocked_until_human_approval():
    review, _ = ready_review()
    with pytest.raises(InvalidReviewTransition, match='human approves'):
        mark_published(review, 'https://github.com/example/project')
    review, requirement = ready_review()
    review = update_requirement(review, requirement.id, status=RequirementStatus.PASSED)
    published = mark_published(approve_review(review), 'https://github.com/example/project')
    assert published.status == ReviewStatus.PUBLISHED
    assert published.repository_url == 'https://github.com/example/project'
    assert published.published_at is not None

def test_blank_feedback_and_requirements_are_rejected():
    with pytest.raises(ValueError):
        Requirement(description='   ')
    review, _ = ready_review()
    with pytest.raises(ValueError):
        request_changes(review, '   ')
