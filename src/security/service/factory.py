from src.security.service.service import PermissionService

_permission_service = PermissionService()


def get_permission_service() -> PermissionService:
    return _permission_service
