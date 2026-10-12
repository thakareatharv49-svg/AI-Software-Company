from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from src.security.authorization import require_company_owner

router = APIRouter(tags=["web"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
PRODUCTS_DIR = Path(__file__).resolve().parents[2] / "generated-products"
LEGACY_PRODUCTS_DIR = Path(__import__("tempfile").gettempdir()) / "ai-software-company-workspaces"

@router.get("/app", dependencies=[Depends(require_company_owner)])
async def company_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )

def _find_product_entrypoint(root: Path) -> tuple[Path, Path] | None:
    """Find a browser entry point at the root or in common frontend output folders."""
    resolved_root = root.resolve()
    for relative in (
        Path("index.html"),
        Path("frontend/index.html"),
        Path("public/index.html"),
        Path("dist/index.html"),
        Path("build/index.html"),
    ):
        candidate = (resolved_root / relative).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate, candidate.parent
    return None


@router.get("/product/{mission_id}", include_in_schema=False, dependencies=[Depends(require_company_owner)])
async def completed_product(mission_id: str) -> RedirectResponse:
    """Open completed products only through the secret-filtered browser sandbox."""
    if not mission_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for char in mission_id
    ):
        raise HTTPException(status_code=404, detail="Product not found")
    return RedirectResponse(
        url=f"/api/missions/{mission_id}/review/live-preview/",
        status_code=307,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/product/{mission_id}/{file_path:path}", include_in_schema=False, dependencies=[Depends(require_company_owner)])
async def completed_product_asset(mission_id: str, file_path: str) -> RedirectResponse:
    """Route legacy asset URLs through the filtered preview asset handler."""
    if not mission_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for char in mission_id
    ):
        raise HTTPException(status_code=404, detail="Product not found")
    normalized = file_path.replace(chr(92), "/")
    if (
        not normalized
        or normalized.startswith("/")
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
        or (len(normalized) >= 2 and normalized[1] == ":")
        or "\\x00" in normalized
    ):
        raise HTTPException(status_code=404, detail="Product file not found")
    return RedirectResponse(
        url=f"/api/missions/{mission_id}/review/live-preview/{quote(normalized, safe='/')}",
        status_code=307,
        headers={"Cache-Control": "no-store"},
    )

@router.get("/api/products", dependencies=[Depends(require_company_owner)])
async def completed_products() -> JSONResponse:
    """List generated apps that have a browser preview; parent-company projects are managed separately."""
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)
    products = []
    roots = list(PRODUCTS_DIR.iterdir())
    if LEGACY_PRODUCTS_DIR.is_dir():
        roots.extend(LEGACY_PRODUCTS_DIR.iterdir())
    seen = set()
    for root in sorted(roots, key=lambda item: item.name):
        if root.name in seen:
            continue
        if not root.is_dir() or _find_product_entrypoint(root) is None:
            continue
        seen.add(root.name)
        products.append({
            "id": root.name,
            "mission_id": root.name,
            "name": root.name.replace("-", " ").replace("_", " ").title(),
            "kind": "generated",
            "status": "preview available",
            "url": f"/product/{root.name}",
        })
    return JSONResponse(products, headers={"Cache-Control": "no-store"})


@router.get("/owner", include_in_schema=False)
async def owner_app() -> FileResponse:
    """Serve the private owner console; the web router is owner-authorized in src.main."""
    return FileResponse(
        STATIC_DIR / "owner-app.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
