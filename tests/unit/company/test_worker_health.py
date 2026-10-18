from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.company.project_factory import ProjectFactory


def _factory_with_active_project(*, last_progress_at, started_at=None):
    factory = object.__new__(ProjectFactory)
    factory.execution_timeout_seconds = 1800.0
    factory.queue = []
    factory._active_project = SimpleNamespace(
        mission=SimpleNamespace(id="mission-1", name="Health check"),
        worker_started_at=started_at or datetime.now(UTC),
        last_progress_at=last_progress_at,
        progress_updates=3,
    )
    return factory


def test_worker_health_reports_idle_without_active_mission():
    factory = object.__new__(ProjectFactory)
    factory.execution_timeout_seconds = 1800.0
    factory.queue = []
    factory._active_project = None

    health = factory.worker_health()

    assert health["status"] == "idle"
    assert health["active_mission_id"] is None
    assert health["heartbeat_age_seconds"] is None


def test_worker_health_reports_recent_heartbeat_as_healthy():
    now = datetime.now(UTC)
    factory = _factory_with_active_project(last_progress_at=now)

    health = factory.worker_health(stale_after_seconds=60)

    assert health["status"] == "healthy"
    assert health["active_mission_id"] == "mission-1"
    assert health["progress_updates"] == 3
    assert health["heartbeat_age_seconds"] < 60


def test_worker_health_flags_stale_heartbeat_without_requeueing():
    old = datetime.now(UTC) - timedelta(seconds=120)
    factory = _factory_with_active_project(last_progress_at=old)
    active = factory._active_project

    health = factory.worker_health(stale_after_seconds=30)

    assert health["status"] == "stale"
    assert "was not cancelled or requeued" in health["diagnostic"]
    assert factory._active_project is active
    assert factory.queue == []


def test_worker_health_defaults_to_execution_timeout():
    old = datetime.now(UTC) - timedelta(seconds=60)
    factory = _factory_with_active_project(last_progress_at=old)

    assert factory.worker_health()["stale_after_seconds"] == 1800.0
    assert factory.worker_health()["status"] == "healthy"


@pytest.mark.parametrize("threshold", [0, -1, float("inf"), float("nan"), True, "30"])
def test_worker_health_rejects_invalid_threshold(threshold):
    factory = object.__new__(ProjectFactory)
    factory.execution_timeout_seconds = 1800.0
    factory.queue = []
    factory._active_project = None

    with pytest.raises(ValueError, match="stale_after_seconds"):
        factory.worker_health(stale_after_seconds=threshold)
