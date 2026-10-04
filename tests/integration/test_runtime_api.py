from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from src.company.runtime.api import create_runtime_app


@dataclass
class FakeState:
    running: bool = False
    queued: int = 0
    processed: int = 0
    failed: int = 0
    worker_count: int = 1


@dataclass
class FakeResult:
    result: str = "completed"
    processed: int = 1
    failed: int = 0


class FakeService:
    def __init__(self) -> None:
        self.started = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False

    async def state(self) -> FakeState:
        return FakeState(running=self.started)

    async def run(self, **kwargs):
        if not self.started:
            raise RuntimeError("Company runtime service is not running.")
        return FakeResult()


def test_health_endpoint():
    client = TestClient(create_runtime_app(FakeService()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_state_endpoint():
    client = TestClient(create_runtime_app(FakeService()))

    response = client.get("/runtime/state")

    assert response.status_code == 200
    assert response.json()["running"] is False


def test_runtime_start_and_stop():
    service = FakeService()
    client = TestClient(create_runtime_app(service))

    assert client.post("/runtime/start").status_code == 200
    assert client.get("/runtime/state").json()["running"] is True

    assert client.post("/runtime/stop").status_code == 200
    assert client.get("/runtime/state").json()["running"] is False


def test_runtime_run_requires_started_service():
    client = TestClient(create_runtime_app(FakeService()))

    response = client.post(
        "/runtime/run",
        json={
            "project_request": {},
            "mission": {},
            "tasks": [],
            "qa_request": {},
            "files": {},
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_runtime_run_endpoint():
    service = FakeService()
    client = TestClient(create_runtime_app(service))

    client.post("/runtime/start")

    response = client.post(
        "/runtime/run",
        json={
            "project_request": {},
            "mission": {},
            "tasks": [],
            "qa_request": {},
            "files": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["result"] == "completed"
