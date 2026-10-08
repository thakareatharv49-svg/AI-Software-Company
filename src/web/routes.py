from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["web"])
STATIC_DIR = Path(__file__).resolve().parent / "static"

@router.get("/app")
async def company_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
