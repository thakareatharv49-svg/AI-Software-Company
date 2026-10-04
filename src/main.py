from fastapi import FastAPI

from api.routes.health import router as health_router
from config.settings import settings
from dashboard.routes.routes import router as dashboard_router
from observability.logging import configure_logging
from src.security.routes.routes import router as security_router

configure_logging()


app = FastAPI(
    title="AI Software Company",
    version="0.1.0",
    description="Autonomous AI software company and continuous software factory",
)

@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    return response




app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(security_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }
