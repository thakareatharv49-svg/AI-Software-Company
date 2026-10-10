from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from api.routes.health import router as health_router
from config.settings import settings
from dashboard.routes.routes import router as dashboard_router
from observability.logging import configure_logging
from src.company.control_center.routes import router as control_router
from src.company.customer_routes import router as customer_router
from src.company.owner_routes import router as owner_router
from src.security.authorization import require_company_owner
from src.security.routes.oauth_routes import router as oauth_router
from src.security.routes.routes import router as security_router
from src.web.routes import router as web_router
from src.web.customer_routes import router as customer_web_router

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
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.include_router(health_router)
app.include_router(dashboard_router, dependencies=[Depends(require_company_owner)])
app.include_router(security_router, dependencies=[Depends(require_company_owner)])
app.include_router(oauth_router)
app.include_router(customer_router)
app.include_router(customer_web_router)
app.include_router(control_router, dependencies=[Depends(require_company_owner)])
app.include_router(owner_router, dependencies=[Depends(require_company_owner)])
app.include_router(web_router)

app.mount(
    "/app/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "web" / "static"),
    name="app-static",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "control_center": "/app",
    }
