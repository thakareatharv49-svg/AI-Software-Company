from fastapi import APIRouter, HTTPException

from src.company.control_center.service import CompanyControlCenter, MissionRecord, MissionSubmission, control_center
from src.company.models.contracts import CompanyState

router = APIRouter(prefix="/api", tags=["company-control"])


def get_control_center() -> CompanyControlCenter:
    return control_center


@router.get("/company/state", response_model=CompanyState)
def company_state() -> CompanyState:
    return get_control_center().state


@router.get("/missions", response_model=list[MissionRecord])
def list_missions() -> list[MissionRecord]:
    return get_control_center().missions()


@router.post("/missions", response_model=MissionRecord, status_code=201)
def submit_mission(submission: MissionSubmission) -> MissionRecord:
    try:
        return get_control_center().submit_mission(submission)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/company/stop", response_model=CompanyState)
def stop_company() -> CompanyState:
    return get_control_center().stop()


@router.post("/company/block", response_model=CompanyState)
def block_company(reason: str = "Paused by operator") -> CompanyState:
    return get_control_center().block(reason)
