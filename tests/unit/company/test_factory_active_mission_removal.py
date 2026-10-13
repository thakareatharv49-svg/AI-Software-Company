import pytest

from src.company.project_factory import ProjectFactory


def test_remove_missions_rejects_active_project_even_after_it_leaves_queue():
    factory = object.__new__(ProjectFactory)
    active = type(
        "Project",
        (),
        {"mission": type("Mission", (), {"id": "active"})()},
    )()
    factory._active_project = active
    factory.queue = []
    factory.store = None

    with pytest.raises(ValueError, match="currently running"):
        factory.remove_missions({"active"})
