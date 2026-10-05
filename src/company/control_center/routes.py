from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.company.control_center.service import (
    CompanyControlCenter,
    MissionRecord,
    MissionSubmission,
    control_center,
)
from src.company.events.events import CompanyEvent
from src.company.models.contracts import CompanyState

router = APIRouter(prefix="/api", tags=["company-control"])
ControlCenter = Annotated[CompanyControlCenter, Depends(lambda: control_center)]


def get_control_center() -> CompanyControlCenter:
    return control_center


@router.get("/company/state", response_model=CompanyState)
def company_state(center: ControlCenter) -> CompanyState:
    return center.state


@router.get("/missions", response_model=list[MissionRecord])
def list_missions(center: ControlCenter) -> list[MissionRecord]:
    return center.missions()


@router.get("/company/events", response_model=list[CompanyEvent])
def company_events(center: ControlCenter) -> list[CompanyEvent]:
    return center.events()


@router.post("/missions", response_model=MissionRecord, status_code=201)
def submit_mission(
    submission: MissionSubmission,
    center: ControlCenter,
) -> MissionRecord:
    try:
        return center.submit_mission(submission)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/company/stop", response_model=CompanyState)
def stop_company(center: ControlCenter) -> CompanyState:
    return center.stop()


@router.post("/company/block", response_model=CompanyState)
def block_company(
    reason: str = "Paused by operator",
    center: ControlCenter = None,
) -> CompanyState:
    return center.block(reason)
