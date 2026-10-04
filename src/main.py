from fastapi import FastAPI

from api.routes.health import router as health_router
from config.settings import settings
from dashboard.routes.routes import router as dashboard_router
from observability.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Autonomous AI software company and continuous software factory",
)

app.include_router(health_router)
app.include_router(dashboard_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }
