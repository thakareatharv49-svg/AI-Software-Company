import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

router = APIRouter(tags=["web"])
STATIC_DIR = Path(__file__).resolve().parent / "static"
PRODUCTS_DIR = Path(__file__).resolve().parents[2] / "generated-products"
LEGACY_PRODUCTS_DIR = Path(__import__("tempfile").gettempdir()) / "ai-software-company-workspaces"

@router.get("/app")
async def company_app() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )

@router.get("/product/{mission_id}", include_in_schema=False)
async def completed_product(mission_id: str) -> HTMLResponse:
    """Open the generated product browser entry point."""
    if not mission_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in mission_id):
        raise HTTPException(status_code=404, detail="Product not found")
    root = (PRODUCTS_DIR / mission_id).resolve()
    base = PRODUCTS_DIR.resolve()
    if not root.is_dir():
        root = (LEGACY_PRODUCTS_DIR / mission_id).resolve()
        base = LEGACY_PRODUCTS_DIR.resolve()
    try:
        root.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Product not found") from exc
    index = root / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="This product has no browser preview")

    # Product URLs have no trailing slash. Without a base URL, relative assets
    # such as style.css and app.js resolve under /product/ instead of this
    # mission asset route, leaving generated apps unstyled and nonfunctional.
    html = index.read_text(encoding="utf-8")
    base_tag = f'<base href="/product/{mission_id}/">'
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

@router.get("/product/{mission_id}/{file_path:path}", include_in_schema=False)
async def completed_product_asset(mission_id: str, file_path: str) -> FileResponse:
    """Serve browser assets belonging to a generated product."""
    if not mission_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in mission_id):
        raise HTTPException(status_code=404, detail="Product not found")
    root = (PRODUCTS_DIR / mission_id).resolve()
    base = PRODUCTS_DIR.resolve()
    if not root.is_dir():
        root = (LEGACY_PRODUCTS_DIR / mission_id).resolve()
        base = LEGACY_PRODUCTS_DIR.resolve()
    target = (root / file_path).resolve()
    try:
        root.relative_to(base)
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Product not found") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Product file not found")
    return FileResponse(target, headers={"Cache-Control": "no-store"})


@router.get("/api/products")
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
        seen.add(root.name)
        if not root.is_dir() or not (root / "index.html").is_file():
            continue
        products.append({
            "mission_id": root.name,
            "url": f"/product/{root.name}",
        })
    return JSONResponse(products, headers={"Cache-Control": "no-store"})
