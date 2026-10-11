"""Dedicated read-only status endpoint for Nexora HQ service-to-service monitoring."""
from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from config.settings import settings
from src.company.control_center.service import CompanyControlCenter, control_center

router = APIRouter(tags=["nexora-hq-integration"])


class HQStatusResponse(BaseModel):
    service: Literal["ai-software-developer"] = "ai-software-developer"
    status: Literal["operational", "degraded", "down", "unknown"]
    active_missions: int = Field(ge=0)
    queued_missions: int = Field(ge=0)
    completed_missions: int = Field(ge=0)
    blocked_missions: int = Field(ge=0)
    updated_at: datetime


def get_hq_status_control_center() -> CompanyControlCenter:
    return control_center


HQStatusControlCenter = Depends(get_hq_status_control_center)


@router.get("/api/hq/status", response_model=HQStatusResponse)
def hq_status(
    request: Request,
    center: CompanyControlCenter = HQStatusControlCenter,
) -> HQStatusResponse:
    """Expose only aggregate counts; mission names, objectives and controls stay private."""
    expected_token = settings.nexora_hq_status_token
    if not expected_token:
        raise HTTPException(status_code=503, detail="HQ status integration is not configured")

    scheme, separator, supplied_token = request.headers.get("authorization", "").partition(" ")
    if (
        scheme.lower() != "bearer"
        or not separator
        or not supplied_token
        or not secrets.compare_digest(supplied_token, expected_token)
    ):
        raise HTTPException(status_code=401, detail="Invalid service credentials")

    jobs = center.mission_jobs()
    counts = {
        "running": 0,
        "queued": 0,
        "completed": 0,
        "blocked": 0,
        "failed": 0,
    }
    for job in jobs:
        status = str(getattr(job.status, "value", job.status)).strip().lower()
        if status in counts:
            counts[status] += 1

    has_blocked_work = counts["blocked"] > 0 or counts["failed"] > 0
    return HQStatusResponse(
        status="degraded" if has_blocked_work else "operational",
        active_missions=counts["running"],
        queued_missions=counts["queued"],
        completed_missions=counts["completed"],
        blocked_missions=counts["blocked"],
        updated_at=datetime.now(UTC),
    )
