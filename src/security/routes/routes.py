from fastapi import APIRouter

from src.security.models.contracts import PermissionDecision, SecurityAction
from src.security.service.factory import get_permission_service

router = APIRouter(prefix="/security", tags=["security"])
_permission_service = get_permission_service()


@router.get("/permissions", response_model=list[PermissionDecision])
def security_permissions() -> list[PermissionDecision]:
    return [
        _permission_service.authorize(SecurityAction.READ),
        _permission_service.authorize(SecurityAction.TOOL_EXECUTE),
        _permission_service.authorize(SecurityAction.GITHUB_READ),
        _permission_service.authorize(SecurityAction.GITHUB_WRITE),
        _permission_service.authorize(SecurityAction.SHELL_EXECUTE),
    ]
