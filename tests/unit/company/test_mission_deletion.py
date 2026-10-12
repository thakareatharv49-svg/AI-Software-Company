from fastapi import HTTPException

from src.company.control_center.routes import delete_mission


class Center:
    def __init__(self, result=None, error=None):
        self.result = result or {"deleted": True, "mission_id": "mission-1"}
        self.error = error
        self.called_with = None

    def delete_mission(self, mission_id):
        self.called_with = mission_id
        if self.error:
            raise self.error
        return self.result


def test_delete_mission_returns_service_result():
    center = Center()

    result = delete_mission("mission-1", center)

    assert result == {"deleted": True, "mission_id": "mission-1"}
    assert center.called_with == "mission-1"


def test_delete_mission_maps_missing_mission_to_404():
    try:
        delete_mission("missing", Center(error=KeyError("missing")))
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Expected missing mission to return 404")


def test_delete_mission_maps_unsafe_delete_to_409():
    try:
        delete_mission("running", Center(error=ValueError("Only queued missions can be deleted")))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected unsafe deletion to return 409")


def test_delete_mission_maps_active_factory_to_409():
    try:
        delete_mission("queued", Center(error=RuntimeError("Stop the factory first")))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected active factory to return 409")
