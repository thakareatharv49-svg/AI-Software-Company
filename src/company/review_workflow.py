from enum import StrEnum
from datetime import UTC, datetime
from uuid import uuid4
from pydantic import BaseModel, Field

class ReviewStatus(StrEnum):
    DRAFT = 'draft'
    IN_REVIEW = 'in_review'
    CHANGES_REQUESTED = 'changes_requested'
    APPROVED = 'approved'
    PUBLISHED = 'published'

class RequirementStatus(StrEnum):
    PENDING = 'pending'
    PASSED = 'passed'
    FAILED = 'failed'

class Requirement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = Field(min_length=1, max_length=1000)
    verification: str = ''
    status: RequirementStatus = RequirementStatus.PENDING
    evidence: str | None = None

class Feedback(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    message: str = Field(min_length=1, max_length=10000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    addressed_in_revision: int | None = None

class ProductReview(BaseModel):
    mission_id: str
    status: ReviewStatus = ReviewStatus.DRAFT
    requirements: list[Requirement] = Field(default_factory=list)
    feedback: list[Feedback] = Field(default_factory=list)
    revision: int = 0
    qa_passed: bool = False
    security_passed: bool = False
    approved_at: datetime | None = None
    published_at: datetime | None = None
    repository_url: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class InvalidReviewTransition(ValueError):
    pass

def _updated(review: ProductReview, **changes) -> ProductReview:
    return review.model_copy(update={**changes, 'updated_at': datetime.now(UTC)}, deep=True)

def prepare_review(review: ProductReview, requirements: list[Requirement], *, qa_passed: bool, security_passed: bool) -> ProductReview:
    if review.status not in {ReviewStatus.DRAFT, ReviewStatus.CHANGES_REQUESTED}:
        raise InvalidReviewTransition(f'Cannot submit for review from {review.status.value}')
    if not requirements:
        raise InvalidReviewTransition('At least one acceptance requirement is required')
    if not qa_passed or not security_passed:
        raise InvalidReviewTransition('Automated QA and security checks must pass before human review')
    return _updated(review, status=ReviewStatus.IN_REVIEW, requirements=requirements, qa_passed=True, security_passed=True, approved_at=None, published_at=None, repository_url=None)

def update_requirement(review: ProductReview, requirement_id: str, *, status: RequirementStatus, evidence: str | None = None) -> ProductReview:
    if review.status != ReviewStatus.IN_REVIEW:
        raise InvalidReviewTransition('Requirements can only be verified while in review')
    found = False
    items = []
    for item in review.requirements:
        if item.id == requirement_id:
            found = True
            items.append(item.model_copy(update={'status': status, 'evidence': evidence}))
        else:
            items.append(item.model_copy(deep=True))
    if not found:
        raise KeyError(requirement_id)
    return _updated(review, requirements=items)

def request_changes(review: ProductReview, message: str) -> ProductReview:
    if review.status not in {ReviewStatus.IN_REVIEW, ReviewStatus.CHANGES_REQUESTED}:
        raise InvalidReviewTransition(f'Cannot request changes from {review.status.value}')
    feedback = Feedback(message=message)
    return _updated(review, status=ReviewStatus.CHANGES_REQUESTED, feedback=[*review.feedback, feedback], revision=review.revision + 1, approved_at=None, published_at=None, repository_url=None)

def approve_review(review: ProductReview) -> ProductReview:
    if review.status != ReviewStatus.IN_REVIEW:
        raise InvalidReviewTransition('Only a product under review can be approved')
    if not review.qa_passed or not review.security_passed:
        raise InvalidReviewTransition('QA and security gates must pass before approval')
    incomplete = [item.description for item in review.requirements if item.status != RequirementStatus.PASSED]
    if incomplete:
        raise InvalidReviewTransition('Acceptance requirements remain unverified: ' + '; '.join(incomplete))
    return _updated(review, status=ReviewStatus.APPROVED, approved_at=datetime.now(UTC))

def mark_published(review: ProductReview, repository_url: str) -> ProductReview:
    if review.status != ReviewStatus.APPROVED:
        raise InvalidReviewTransition('GitHub publication is blocked until the human approves the product')
    url = repository_url.strip()
    if not url.startswith('https://'):
        raise ValueError('Repository URL must be an HTTPS URL')
    return _updated(review, status=ReviewStatus.PUBLISHED, repository_url=url, published_at=datetime.now(UTC))
