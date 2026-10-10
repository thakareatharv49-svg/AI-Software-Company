import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
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
async def completed_product(mission_id: str) -> HTMLResponse:
    """Open the generated product browser entry point."""
    if not mission_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in mission_id):
        raise HTTPException(status_code=404, detail="Product not found")
    candidates = (
        ((PRODUCTS_DIR / mission_id).resolve(), PRODUCTS_DIR.resolve()),
        ((LEGACY_PRODUCTS_DIR / mission_id).resolve(), LEGACY_PRODUCTS_DIR.resolve()),
    )
    root = None
    index = None
    asset_root = None
    for candidate, base in candidates:
        try:
            candidate.relative_to(base)
        except ValueError:
            continue
        if not candidate.is_dir():
            continue
        entrypoint = _find_product_entrypoint(candidate)
        if entrypoint is not None:
            index, asset_root = entrypoint
            root = candidate
            break
    if root is None or index is None or asset_root is None:
        if any(candidate.is_dir() for candidate, _ in candidates):
            raise HTTPException(
                status_code=404,
                detail="This product has no browser preview (expected index.html in the product root, frontend, public, dist, or build folder)",
            )
        raise HTTPException(status_code=404, detail="Product not found")

    # Product URLs have no trailing slash. Without a base URL, relative assets
    # such as style.css and app.js resolve under /product/ instead of this
    # mission asset route, leaving generated apps unstyled and nonfunctional.
    html = index.read_text(encoding="utf-8")
    asset_prefix = asset_root.relative_to(root).as_posix()
    base_path = f"/product/{mission_id}/"
    if asset_prefix != ".":
        base_path += asset_prefix.rstrip("/") + "/"
    base_tag = f'<base href="{base_path}">'
    head_pattern = r"(<head(?:\s[^>]*)?>)"
    if re.search(head_pattern, html, flags=re.IGNORECASE):
        html = re.sub(
            head_pattern,
            lambda match: match.group(1) + base_tag,
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        html = base_tag + html
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})

@router.get("/product/{mission_id}/{file_path:path}", include_in_schema=False, dependencies=[Depends(require_company_owner)])
async def completed_product_asset(mission_id: str, file_path: str) -> FileResponse:
    """Serve browser assets belonging to a generated product."""
    if not mission_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in mission_id):
        raise HTTPException(status_code=404, detail="Product not found")
    target = None
    for candidate, base in (
        ((PRODUCTS_DIR / mission_id).resolve(), PRODUCTS_DIR.resolve()),
        ((LEGACY_PRODUCTS_DIR / mission_id).resolve(), LEGACY_PRODUCTS_DIR.resolve()),
    ):
        try:
            candidate.relative_to(base)
            candidate_target = (candidate / file_path).resolve()
            candidate_target.relative_to(candidate)
        except ValueError:
            continue
        if candidate.is_dir() and candidate_target.is_file():
            target = candidate_target
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Product file not found")
    return FileResponse(target, headers={"Cache-Control": "no-store"})


@router.get("/api/products", dependencies=[Depends(require_company_owner)])
async def completed_products() -> JSONResponse:
    """List generated browser products that actually have an index.html."""
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
            "mission_id": root.name,
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
