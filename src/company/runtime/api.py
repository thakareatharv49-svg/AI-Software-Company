from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.company.runtime.service import CompanyRuntimeService


class RuntimeRunRequest(BaseModel):
    project_request: Any
    mission: Any
    tasks: list[Any] = Field(default_factory=list)
    qa_request: Any
    files: dict[str, str] = Field(default_factory=dict)
    agent_executor: Any = None
    repair_agent_executor: Any = None
    github_repository: Any = None
    pull_request_head: str | None = None


def create_runtime_app(service: CompanyRuntimeService) -> FastAPI:
    if service is None:
        raise ValueError("service is required")

    app = FastAPI(title="Autonomous AI Company Runtime")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/runtime/state")
    async def runtime_state() -> dict[str, Any]:
        state = await service.state()
        return asdict(state)

    @app.post("/runtime/start")
    async def runtime_start() -> dict[str, str]:
        await service.start()
        return {"status": "started"}

    @app.post("/runtime/stop")
    async def runtime_stop() -> dict[str, str]:
        await service.stop()
        return {"status": "stopped"}

    @app.post("/runtime/run")
    async def runtime_run(request: RuntimeRunRequest) -> dict[str, Any]:
        try:
            result = await service.run(**request.model_dump())
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        if hasattr(result, "__dict__"):
            return result.__dict__

        return {"result": result}

    return app
