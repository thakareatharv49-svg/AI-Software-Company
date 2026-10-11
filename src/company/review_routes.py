from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.company.control_center.routes import get_control_center
from src.company.control_center.service import CompanyControlCenter
from src.company.mission_jobs import MissionJobStatus
from src.company.review_store import ProductReviewStore
from src.company.review_workflow import (
    ProductReview,
    Requirement,
    RequirementStatus,
    approve_review,
    mark_published,
    prepare_review,
    request_changes,
    update_requirement,
)
from src.config.settings import settings
from src.github.automation.automation import GitHubAutomation
from src.github.client.http import GitHubHttpClient
from src.github.models.contracts import GitHubRepository
from src.company.github_native.service import GitHubNativeService

router = APIRouter(prefix='/api/missions', tags=['product-review'])
PRODUCTS_ROOT = Path(__file__).resolve().parents[2] / 'generated-products'


class SubmitReviewRequest(BaseModel):
    requirements: list[Requirement] = Field(min_length=1, max_length=200)


class RequirementUpdateRequest(BaseModel):
    status: RequirementStatus
    evidence: str | None = Field(default=None, max_length=4000)


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)

    def model_post_init(self, __context: object) -> None:
        self.message = self.message.strip()
        if not self.message:
            raise ValueError('Feedback cannot be blank')


@lru_cache(maxsize=1)
def _review_store() -> ProductReviewStore:
    return ProductReviewStore()


def _get_job(mission_id: str, center: CompanyControlCenter):
    job = center.mission_job(mission_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Mission job not found')
    return job


def _get_review(mission_id: str, center: CompanyControlCenter) -> ProductReview:
    _get_job(mission_id, center)
    review = _review_store().get(mission_id)
    if review is None:
        review = ProductReview(mission_id=mission_id)
        _review_store().save(review)
    return review


def _workspace_files(mission_id: str) -> tuple[Path, dict[str, str]]:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', mission_id):
        raise HTTPException(status_code=404, detail='Product workspace not found')
    root = (PRODUCTS_ROOT / mission_id).resolve()
    try:
        root.relative_to(PRODUCTS_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail='Product workspace not found') from exc
    if not root.is_dir():
        raise HTTPException(status_code=404, detail='Generated product workspace not found')

    ignored = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache'}
    files: dict[str, str] = {}
    total_bytes = 0
    for target in sorted(root.rglob('*')):
        if not target.is_file() or target.is_symlink():
            continue
        relative = target.relative_to(root)
        if any(part in ignored for part in relative.parts):
            continue
        try:
            resolved = target.resolve()
            resolved.relative_to(root)
        except ValueError:
            continue
        if target.stat().st_size > 1_000_000:
            raise HTTPException(status_code=413, detail=f'Generated file is too large to publish: {relative.as_posix()}')
        try:
            content = target.read_text(encoding='utf-8')
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail=f'Generated file is not UTF-8 text: {relative.as_posix()}') from exc
        total_bytes += len(content.encode('utf-8'))
        files[relative.as_posix()] = content
        if len(files) > 200 or total_bytes > 10_000_000:
            raise HTTPException(status_code=413, detail='Generated product exceeds safe publishing limits')
    if not files:
        raise HTTPException(status_code=422, detail='Generated product contains no publishable files')
    return root, files


def _repository_name(name: str, mission_id: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9._-]+', '-', name.strip())
    slug = re.sub(r'-{2,}', '-', slug).strip('-._') or 'generated-project'
    return f'{slug}-{mission_id[:8]}'


@router.get('/{mission_id}/review', response_model=ProductReview)
def get_product_review(
    mission_id: str,
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> ProductReview:
    return _get_review(mission_id, center)


@router.post('/{mission_id}/review/submit', response_model=ProductReview)
def submit_product_for_review(
    mission_id: str,
    payload: SubmitReviewRequest,
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> ProductReview:
    job = _get_job(mission_id, center)
    if job.status != MissionJobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail='Only a completed, QA-checked product can enter human review')
    if not (PRODUCTS_ROOT / mission_id).is_dir():
        raise HTTPException(status_code=409, detail='Generated product workspace is unavailable for review')
    review = _get_review(mission_id, center)
    try:
        updated = prepare_review(
            review,
            payload.requirements,
            qa_passed=True,
            security_passed=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _review_store().save(updated)
    return updated


@router.patch('/{mission_id}/review/requirements/{requirement_id}', response_model=ProductReview)
def verify_product_requirement(
    mission_id: str,
    requirement_id: str,
    payload: RequirementUpdateRequest,
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> ProductReview:
    review = _get_review(mission_id, center)
    try:
        updated = update_requirement(
            review,
            requirement_id,
            status=payload.status,
            evidence=payload.evidence,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Acceptance requirement not found') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _review_store().save(updated)
    return updated


@router.post('/{mission_id}/review/feedback', response_model=ProductReview)
async def submit_product_feedback(
    mission_id: str,
    payload: FeedbackRequest,
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> ProductReview:
    job = _get_job(mission_id, center)
    if job.status != MissionJobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail='Wait until the current revision finishes before requesting changes')
    review = _get_review(mission_id, center)
    try:
        updated = request_changes(review, payload.message)
        revised_job = center._factory.revise(mission_id, payload.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail='Mission job not found') from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    center._sync_mission_from_job(revised_job)
    _review_store().save(updated)
    try:
        await center.run_factory(max_projects=1, max_retries=2, mission_id=mission_id)
    except (RuntimeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=f'Revision is queued but the factory could not start: {exc}') from exc
    return updated


@router.post('/{mission_id}/review/approve', response_model=ProductReview)
def approve_product(
    mission_id: str,
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> ProductReview:
    review = _get_review(mission_id, center)
    try:
        updated = approve_review(review)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _review_store().save(updated)
    return updated


@router.post('/{mission_id}/review/publish', response_model=ProductReview)
async def publish_approved_product(
    mission_id: str,
    center: Annotated[CompanyControlCenter, Depends(get_control_center)],
) -> ProductReview:
    job = _get_job(mission_id, center)
    review = _get_review(mission_id, center)
    if review.status.value != 'approved':
        raise HTTPException(status_code=409, detail='Approve the current product revision before publishing')
    if job.status != MissionJobStatus.COMPLETED:
        raise HTTPException(status_code=409, detail='Only completed products can be published')
    if not (settings.github_allow_writes and settings.github_token and settings.github_repository_owner):
        raise HTTPException(status_code=503, detail='GitHub publishing is not configured')

    _, files = _workspace_files(mission_id)
    repository = GitHubRepository(
        owner=settings.github_repository_owner,
        name=_repository_name(job.mission.name, mission_id),
        default_branch=settings.github_default_branch,
    )
    github = GitHubAutomation(
        GitHubHttpClient(token=settings.github_token, api_url=settings.github_api_base_url)
    )
    result = await GitHubNativeService(github=github).publish_files(
        repository,
        settings.github_default_branch,
        files,
        f'feat: publish approved {job.mission.name}',
    )
    if not result.success:
        raise HTTPException(status_code=502, detail=f'GitHub publishing failed; product remains approved: {result.message}')
    updated = mark_published(review, f'https://github.com/{repository.owner}/{repository.name}')
    _review_store().save(updated)
    return updated
